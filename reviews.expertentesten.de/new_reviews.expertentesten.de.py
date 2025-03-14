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
    revs_json = data.xpath('//script[not(@id) and contains(., "json")]/text()').string()
    if not revs_json:
        return

    revs_json = simplejson.loads(revs_json.split('let json = ')[-1].split('; let json_filter')[0])
    names = revs_json.get('name')
    for i in range(1, len(names)):
        product = Product()
        product.url = context['url']
        product.category = context['cat']

        name = data.parse_fragment(names[i])
        product.name = name.xpath('//span[not(@class)]/text()').string()
        product.ssid = product.name.lower().replace(' ', '-')
        product.manufacturer = name.xpath('//span/@data-brand').string()

        review = Review()
        review.type = 'pro'
        review.url = product.url
        review.ssid = product.ssid
        review.title = context['title']

        date = data.xpath('//meta[@property="article:modified_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//div[@class="v3-author-social"]/a/@aria-label').string()
        author_url = data.xpath('//div[@class="v3-author-social"]/a/@href').string()
        if author and author_url:
            author = author.split(' - ')[0]
            author_ssid = author_url.split('/')[-2]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            author = author.split(' - ')[0]
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = data.parse_fragment(revs_json.get('rating')[i]).xpath('//span/strong/text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace(',', '.').strip(' -')
            if grade_overall:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=1.0, worst=6.0))

        for j in range(2, 5):
            grade = data.parse_fragment(revs_json.get('attributes')[j][i]).xpath('//span/@style').string()
            if grade:
                grade_name = revs_json.get('attributes')[j][0].strip()
                grade = float(grade.split()[-1].replace('%', '')) / 10
                review.grades.append(Grade(name=grade_name, value=grade, best=10.0))

        pros = data.parse_fragment(revs_json.get('attributes')[7][i]).xpath('//li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = data.parse_fragment(revs_json.get('attributes')[8][i]).xpath('//li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        excerpt = data.parse_fragment(revs_json.get('attributes')[1][i]).xpath('.//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip(' "')
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
