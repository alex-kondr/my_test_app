from agent import *
from models.products import *


XCAT = ['ERBJUDANDEN', 'Kontakter']
XSUBCAT = ['Enligt metoden för bryggning', 'Varumärken', 'För Företag', 'Tips för rengöring av din kaffemaskin', 'Köksapparater varumärken', 'Packning']


def run(context, session):
    session.queue(Request('https://www.coffeefriend.se/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul[@class="main-navigation__container nav-cached"]/li')
    for cat in cats:
        cat_name = cat.xpath('a/text()').string()

        if cat_name not in XCAT:
            sub_cats = cat.xpath('ul/li')
            for sub_cat in sub_cats:
                sub_cat_name = sub_cat.xpath('span/text()').string()

                if sub_cat_name not in XSUBCAT:
                    sub_cats1 = sub_cat.xpath('ul/li')
                    for sub_cat1 in sub_cats1:
                        sub_cat1_name = sub_cat1.xpath('a/text()').string()
                        url = sub_cat1.xpath('a/@href').string()

                        if sub_cat1_name.startswith('All') or sub_cat1_name == sub_cat_name:
                            session.queue(Request(url+'?orderby=rating', use='curl', options='--data-raw "ppp=48"', max_age=0), process_prodlist, dict(cat=cat_name+'|'+sub_cat_name))
                        else:
                            session.queue(Request(url+'?orderby=rating', use='curl', options='--data-raw "ppp=48"', max_age=0), process_prodlist, dict(cat=cat_name+'|'+sub_cat_name+'|'+sub_cat1_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="row"]/ul/li')
    for prod in prods:
        name = prod.xpath('div/@data-name').string()
        sku = prod.xpath('div/@data-sku').string()
        ssid = prod.xpath('div/@data-id').string()
        url = prod.xpath('.//a[@itemprop="url"]/@href').string()

        revs_count = prod.xpath('.//span[@itemprop="reviewCount"]/text()').string()
        if revs_count and int(revs_count) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, sku=sku, ssid=ssid, url=url))
        else:
            return

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url+'?orderby=rating', use='curl', options='--data-raw "ppp=48"', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('|Typ', '')
    product.ssid = context['ssid']
    product.sku = context['sku']
    product.manufacturer = data.xpath('//div[@class="spec" and contains(., "Tillverkare")]/div[not(text()="Tillverkare")]/text()').string()

    ean = data.xpath('//div[@class="spec" and contains(., "EAN")]/div[not(text()="EAN")]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product
    process_review(data, context, session)


def process_review(data, context, session):
    revs = data.xpath('//body[div[@class="comment-info"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['product'].url
        review.date = rev.xpath('./following-sibling::body[1]/div[@class="comment-date"]/text()').string()

        author = rev.xpath('.//div[@class="user-name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('./following-sibling::head[1]/meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        helpful = rev.xpath('./following-sibling::body[1]//span[@class="useful"]/text()').string()
        if helpful and int(helpful) > 0:
            review.add_property(type='helpful_votes', value=int(helpful))

        not_helpful = rev.xpath('./following-sibling::body[1]//span[@class="not-useful"]/text()').string()
        if not_helpful and int(not_helpful) > 0:
            review.add_property(type='not_helpful_votes', value=int(not_helpful))

        excerpt = rev.xpath('./following-sibling::body[1]//p/text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            context['product'].reviews.append(review)

    if data.xpath('//span[text()="Nästa"]/text()').string():
        next_page = context.get('page', 1) + 1
        next_url = context['product'].url + 'comment-page-' + str(next_page) + '/'
        session.queue(Request(next_url), process_review, dict(context, page=next_page))

    elif context['product'].reviews:
        session.emit(context['product'])
