from agent import *
from models.products import *


XCAT = ['Accessories', 'Content Creators']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.sweetwater.com'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="assets-site-header__nav-menu-item mn-top-level"]')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        if name and name not in XCAT:
            sub_cats = cat.xpath('.//a[contains(@id, "mn-col-headline")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string(multiple=True) if 'More ' not in sub_name else ''

                sub_cats1 = sub_cat.xpath('following-sibling::div[contains(@data-headline-id, "mn-col-headline")][1]/a')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string(multiple=True)

                    if 'All ' not in sub_name1:
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url + '?sb=reviews'), process_prodlist, dict(cat=(name + '|' + sub_name + '|' + sub_name1).replace('||', '|')))
                else:
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url + '?sb=reviews'), process_prodlist, dict(cat=(name + '|' + sub_name).replace('||', '|')))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-card__info"]')
    for prod in prods:
        name = prod.xpath('h2[@class="product-card__name"]//a/text()').string()
        ssid = prod.xpath('div/@data-serial').string()
        sku = prod.xpath('div/@data-itemid').string()
        url = prod.xpath('h2[@class="product-card__name"]//a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="rating__count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, sku=sku, url=url))
        else:
            return

    next_url = data.xpath('//a[@class="paginate-next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = context['sku']
    product.category = context['cat']

    mpn = data.xpath('//li[.//strong[contains(., "Manufacturer")]]//span[@class="table__cell"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    session.queue(Request(product.url + '/reviews'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//body[h3[@class="review-customer-box__title"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author, date = rev.xpath('.//span[@class="review-customer-box__subhead"]/text()').string().split(' on ')

        date = date.strip()
        if date:
            review.date = date

        author = author.split('By ')[-1].split('from ')[0].strip()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = data.xpath('p[@class="review-customer-box__comments"]//span[string-length() > 1]/@data-rated[last()]')
