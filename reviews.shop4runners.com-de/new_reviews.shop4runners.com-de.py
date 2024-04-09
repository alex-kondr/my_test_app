from agent import *
from models.products import *


XCAT = ['Laufen', 'WEITERE', 'NEUHEITEN', 'BESTSELLER', 'Sale', 'Bestseller']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://shop4runners.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[a[@class="lg:hidden w-full h-full flex items-center justify-center cursor-pointer"]]')
    for cat in cats:
        name = cat.xpath('div[@class="lg:p-3"]/text()').string()

        sub_cats = cat.xpath('.//div[contains(@class, "category-item nav-item-wrapper nav-item-wrapper--and-text bg-white bg-white border-b lg:border-b-0 lg:inline-block itm-")]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div/div/a[@class="nav-item__title uppercase no-underline"]/text()').string()

            if sub_name and sub_name not in XCAT:
                sub_cats1 = sub_cat.xpath('.//div[@class="category-item nav-item-wrapper nav-item-wrapper--and-text bg-white bg-white border-b lg:border-b-0 lg:inline-block"]|.//a[contains(@class, "nav-item__title lg:hover:bg-neutral-90")]')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('(.//div[@class="nav-item__title uppercase"]/text()|text())[normalize-space()]').string()

                    if sub_name1 not in XCAT:
                        sub_cats2 = sub_cat1.xpath('.//div[@class="nav-item nav-item__link"]/a')

                        if sub_cats2:
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.xpath('text()').string()
                                url = sub_cat2.xpath('@href').string()
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                        else:
                            url = sub_cat1.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

                else:
                    url = sub_cat.xpath('div/div/a[@class="nav-item__title uppercase no-underline"]/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-info")]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-item-link"]//text()[normalize-space()]').string(multiple=True)
        url = prod.xpath('.//a[@class="product-item-link"]/@href').string()

        rating = prod.xpath('.//div[@class="rating-number ml-2 text-md"]/span/text()').string()
        if rating and float(rating) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.sku = data.xpath('//meta[@itemprop="sku"]/@coontent').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="sku"]/preceding-sibling::meta[@itemprop="name"]/@content').string()

    mpn = data.xpath('//meta[@itemprop="gtin"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//section/@data-loadbee-gtin').striing()
    if ean and ean.isdigit() and len(ean) > 12:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']
    
    revs_cnt = int(data.xpath('//span[@class="reviews text-base-v2 relative -top-px"]/text()').string().strip('()').split()[0])
    if revs_cnt > data.xpath('count(//div[@itemprop="review"])'):
        raise ValueError(">>>>>>>>>>>>>>>")
    elif revs_cnt == data.xpath('count(//div[@itemprop="review"])'):
        print("Good")

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//strong[@itemprop="author"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[@class="rating-summary__star"])')
        if grade_overall:
            review.grades(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('div[@itemprop="name"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page