from agent import *
from models.products import *


XCAT = ['Service', 'SALE!']


def run(context, session):
    session.queue(Request('https://www.wlan-shop24.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="cat-ul"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        if name and name not in XCAT:
            cats1 = cat.xpath('ul/li/div/div/div[a]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/span[contains(@class, "title")]/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()
                            session.queue(Request(url), process_category, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('a/@href').string()
                        session.queue(Request(url), process_category, dict(cat=name+'|'+cat1_name))


# def process_category(data, context, session):
#     subcats = data.xpath('//div[@class="sub-categories"]')
#     if not subcats:
#         process_prodlist(data, context, session)
#         return

#     for subcat in subcats:
#         name = subcat.xpath('div[contains(@class, "caption")]/text()').string()
#         url = subcat.xpath('a/@href').string()
#         session.queue(Request(url), process_category, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="productbox-inner"]')
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "text")]/text()').string()
        url = prod.xpath('.//a[contains(@class, "text")]/@href').string()

        rating = prod.xpath('a[@class="rating"]')
        if rating:
            session.queue(Request(url+'?ratings_nItemsPerPage=-1'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@itemprop="brand"]/@content').string()
    product.ssid = data.xpath('//script/@data-product-id').string()
    product.sku = product.ssid

    ean = data.xpath('//div[contains(@itemprop, "gtin")]/@content').string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    mpn = data.xpath('//div[@itemprop="mpn"]/@content').string()
    if mpn and len(mpn) > 5:
        product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs = data.xpath('//div[contains(@class, "review-comment")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().replace('comment', '')

        title = rev.xpath('.//span[@class="subheadline"]/text()').string(multiple=True)
        if title:
            review.title = title.strip()

        date = rev.xpath('.//div[@class="blockquote-footer"]/text()').string(multiple=True)
        if date:
            review.date = date.strip(' ,')

        author = rev.xpath('.//div[@class="blockquote-footer"]/span/span/text()').string(multiple=True)
        if author and author.strip():
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.xpath('.//span[@class="verified-purchase"]/text()')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.xpath('.//span[@class="rating"]/@title').string()
        if grade_overall:
            grade_overall = grade_overall.split(': ')[-1].split('/')[0]
            if grade_overall:
                review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//blockquote/p//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip()
            if excerpt:
                review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # Loaded all revs
