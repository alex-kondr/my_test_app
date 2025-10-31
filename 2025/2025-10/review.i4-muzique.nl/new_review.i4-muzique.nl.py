from agent import *
from models.products import *


XCAT = ["Home", "Blog", "About", "Contact", "Shop", "SALE !!!"]


def run(context, session):
    session.queue(Request("https://i4studio.nl/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//ul[@id='menu-nieuw']/li")
    for cat in cats:
        name = cat.xpath("a//text()").string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath("div/div/ul/li")
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath("a//text()").string(multiple=True)
                    url = sub_cat.xpath("a/@href").string()

                    if sub_name not in XCAT:
                        session.queue(Request(url), process_prodlist, dict(cat=name+'|'+sub_name))
            else:
                url = cat.xpath("a/@href").string()
                session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//li[contains(@class, 'product type-product')]")
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product__link")]/text()').string(multiple=True)
        url = prod.xpath('.//a[contains(@class, "product__link")]/@href').string()
        ssid = prod.xpath(".//a/@data-product-id").string()
        mpn = prod.xpath(".//a/@data-product_sku").string()
        revs_cnt = prod.xpath(".//div/@data-number-of-reviews").string()

        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, mpn=mpn))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.sku = product.ssid
    product.category = context["cat"]

    if context['mpn'] and ' ' not in context['mpn']:
        product.add_property(type='id.manufacturer', value=context['mpn'])

    ean = data.xpath("//tr[contains(@class, '--attribute_ean')]/td//text()").string(multiple=True)
    if ean:
        product.add_property(type="id.ean", value=ean)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath("//div[@class='jdgm-rev-widg__reviews']/div")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = rev.xpath("@data-review-id").string()

        date = rev.xpath(".//span[contains(@class, 'timestamp')]/@data-content").string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath(".//span[contains(@class, 'author')]/text()").string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = data.xpath(".//span/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath("@data-verified-buyer").string()
        if is_verified and is_verified == "true":
            review.add_property(type='is_verified_buyer', value=True)
        elif is_verified and is_verified == "false":
            review.add_property(type='is_verified_buyer', value=False)

        title = rev.xpath(".//b[@class='jdgm-rev__title']/text()").string()
        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    next_page = data.xpath('//a[@rel="next"]/@data-page').string()
    if next_page:
        next_page = int(next_page)
        next_url = 'https://judge.me/reviews/reviews_for_widget?url=i4studio.nl&shop_domain=i4studio.nl&platform=woocommerce&page={page}&per_page=5&product_id={ssid}'.format(page=next_page, ssid=product.ssid)
        session.do(Request(next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
