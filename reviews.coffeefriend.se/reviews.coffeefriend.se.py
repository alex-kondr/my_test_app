from agent import *
from models.products import *


XCAT = ['ERBJUDANDEN', 'Kontakter']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.coffeefriend.se/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="main-navigation__container nav-cached"]/li')
    for cat in cats:
        cat_name = cat.xpath('a/text()').string()

        if cat_name not in XCAT:
            sub_cats = cat.xpath('ul/li')
            for sub_cat in sub_cats:
                sub_cat_name = sub_cat.xpath('span/text()').string()

                sub_cats1 = sub_cat.xpath('ul/li')
                for sub_cat1 in sub_cats1:
                    sub_cat1_name = sub_cat1.xpath('a/text()').string()
                    url = sub_cat1.xpath('a/@href').string()
                    session.queue(Request(url+'?orderby=rating', use='curl', options='--data-raw "ppp=48"', max_age=0), process_prodlist, dict(cat=cat_name+'|'+sub_cat_name+'|'+sub_cat1_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="row"]/ul/li')
    count_prods = data.xpath('count(//div[@class="row"]/ul/li)')
    count_prods_revs = 0
    for prod in prods:
        revs_count = prod.xpath('.//span[@itemprop="reviewCount"]/text()').string()
        if not revs_count or int(revs_count) == 0:
            break

        count_prods_revs += 1
        name = prod.xpath('div/@data-name').string()
        sku = prod.xpath('div/@data-sku').string()
        id = prod.xpath('div/@data-id').string()
        url = prod.xpath('.//a[@itemprop="url"]/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, sku=sku, id=id, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if count_prods == count_prods_revs and next_url:
        session.queue(Request(next_url+'?orderby=rating', use='curl', options='--data-raw "ppp=48"', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = context['url'].split('/')[-1]
    product.sku = context['sku']
    product.manufacturer = data.xpath('//div[@class="spec" and contains(., "Tillverkare")]/div[not(text()="Tillverkare")]/text()').string()
    product.add_property(type='id.manufacturer', value=context['id'])

    ean = data.xpath('//div[@class="spec" and contains(., "EAN")]/div[not(text()="EAN")]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//body[div[@class="comment-info"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('./following-sibling::body[1]/div[@class="comment-date"]/text()').string()

        helpful = rev.xpath('./following-sibling::body[1]//span[@class="useful"]/text()').string()
        not_helpful = rev.xpath('./following-sibling::body[1]//span[@class="not-useful"]/text()').string()
        if (helpful or not_helpful) and (int(helpful) > 0 or int(not_helpful) > 0):
            review.add_property(type='helpful_votes', value=int(helpful))
            review.add_property(type='not_helpful_votes', value=int(not_helpful))

        grade_overall = rev.xpath('./following-sibling::head[1]/meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        author = rev.xpath('.//div[@class="user-name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath('./following-sibling::body[1]//p/text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
