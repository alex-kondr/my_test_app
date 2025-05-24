from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.startech.com.bd/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="nav-item has-child"]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul[contains(@class, "drop-menu-1")]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/text()').string()

            if not any([' Offer' in sub_name, sub_name.startswith('All '), sub_name.startswith('Show All '), sub_name.startswith('Brand ')]):
                sub_cats1 = sub_cat.xpath('ul[contains(@class, "drop-menu-2")]/li/a')

                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string()
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url + '?limit=90', use='curl', force_charset="utf-8"), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url + '?limit=90', use='curl', force_charset="utf-8"), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//h4[contains(@class, "item-name")]/a')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset="utf-8"), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset="utf-8"), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//td[contains(@class, "product-code")]/text()').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//td[contains(@class, "product-brand")]/text()').string()

    revs_cnt1 = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    revs_cnt2 = data.xpath('count(//div[@id="review"])')
    if revs_cnt1 and float(revs_cnt1) != revs_cnt2:
        raise ValueError('!!!!!!!!')

    revs = data.xpath('//div[@id="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//p[@class="author"]/text()').string(multiple=True)
        if date:
            review.date = date.split('on ')[-1].strip()

        author = rev.xpath('.//span[@class="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//span[@class="rating"]/span[contains(., "star")])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//p[@class="review"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
