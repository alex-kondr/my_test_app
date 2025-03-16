from agent import *
from models.products import *
import simplejson


XCAT = ['Home', 'Services']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.expertentesten.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[not(@id or @itemtype) and @class="menu"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//ul[@class="category-meta-list"]/li/a')
    for sub_cat in sub_cats:
        name = sub_cat.xpath('text()').string(multiple=True)
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=context['cat'] + '|' + name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="category-topics-list-item"]/p/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_reviews, dict(context, title=title, url=url))


def process_reviews(data, context, session):
    revs_json = data.xpath('''//script[contains(., '"attributes"')]/text()''').string()
    if not revs_json:
        return

    revs_json = simplejson.loads(revs_json.split('let json = ')[-1].split('; let json_filter')[0])
    names = revs_json.get('name')
    for i in range(1, len(names)):
        product = Product()
        product.name = names[i].split('data-brand="')[-1].split('"')[0]
        product.ssid = product.name.lower().replace(' ', '-')
        product.category = context['cat']

        amazon_rating = revs_json.get('amazon_rating')
        if amazon_rating:
            product.url = data.parse_fragment(amazon_rating[i]).xpath('//a/@href').string()
        else:
            product.url = context['url']

        offer = revs_json.get('offer')
        if offer:
            mpn = data.parse_fragment(offer[i]).xpath('//span/@data-asin').string()
            if mpn:
                product.add_property(type='id.manufacturer', value=mpn)

        review = Review()
        review.type = 'pro'
        review.url = context['url']
        review.ssid = product.ssid
        review.title = context['title']

        date = data.xpath('//meta[@property="article:modified_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//div[@class="v3-author-right"]/span[@class="author-name"]/text()').string()
        author_url = data.xpath('//div[@class="v3-author-social"]/a/@href').string()
        if author and author_url:
            author = author.split(' - ')[0]
            author_ssid = author_url.split('/')[-2]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            author = author.split(' - ')[0]
            review.authors.append(Person(name=author, ssid=author))

        rating = revs_json.get('rating')
        if rating:
            grade_overall = data.parse_fragment(rating[i]).xpath('//span/strong/text()').string()
            if grade_overall:
                grade_overall = grade_overall.replace(',', '.').strip(' -')
                if grade_overall:
                    review.grades.append(Grade(type='overall', value=float(grade_overall), best=1.0, worst=6.0))

        for attribute in revs_json.get('attributes', []):

            if '%' in attribute[1]:
                grade = data.parse_fragment(attribute[i]).xpath('//span/@style').string()
                if grade:
                    grade_name = attribute[0].strip()
                    grade = float(grade.split()[-1].replace('%', '')) / 10
                    if grade > 10:
                        grade = 10.0
                    review.grades.append(Grade(name=grade_name, value=grade, best=10.0))

            if 'Vorteile' in attribute[0]:
                pros = data.parse_fragment(attribute[i]).xpath('//li')
                for pro in pros:
                    pro = pro.xpath('.//text()').string(multiple=True).replace('kA', '').strip(' "<>')
                    if len(pro) > 1:
                        review.add_property(type='pros', value=pro)

            if 'Nachteile' in attribute[0]:
                cons = data.parse_fragment(attribute[i]).xpath('//li')
                for con in cons:
                    con = con.xpath('.//text()').string(multiple=True).replace('kA', '').strip(' "<>')
                    if len(con) > 1:
                        review.add_property(type='cons', value=con)

            if 'Testergebnis' in attribute[0]:
                excerpt = data.parse_fragment(attribute[i]).xpath('.//text()').string(multiple=True)
                if excerpt:
                    excerpt = excerpt.replace('kA', '').strip(' "<>')
                    if len(excerpt) > 2:
                        review.add_property(type='excerpt', value=excerpt)

                        product.reviews.append(review)

        if product.reviews:
            session.emit(product)
