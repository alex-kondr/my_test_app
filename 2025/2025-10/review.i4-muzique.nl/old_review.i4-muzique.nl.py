from agent import *
from models.products import *


XCAT = ["Home", "Blog", "About", "Contact", "Shop"]


def run(context, session):
    session.queue(Request("https://i4studio.nl/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats1 = data.xpath("//ul[@id='menu-nieuw']/li")
    for cat1 in cats1:
        cat1_name = cat1.xpath("a//text()").string(multiple=True)
        url = cat1.xpath("a/@href").string()
        cats2 = cat1.xpath("div/div/ul/li")
        if cat1_name not in XCAT:
            if not cats2:
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name))
            for cat2 in cats2:
                cat2_name = cat2.xpath("a//text()").string(multiple=True)
                url = cat2.xpath("a/@href").string()
                cats3 = cat2.xpath("div/div/ul/li/a")
                if not cats3:
                    session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))
                for cat3 in cats3:
                    cat3_name = cat3.xpath(".//text()").string(multiple=True)
                    url = cat3.xpath("@href").string()
                    session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//li[contains(@class, 'product type-product')]")
    for prod in prods:
        name = prod.xpath('div[@class="woocommerce-image__wrapper"]/a/@aria-label').string()
        url = prod.xpath('div[@class="woocommerce-image__wrapper"]/a/@href').string()
        ssid = prod.xpath(".//a/@data-product-id").string()
        sku = prod.xpath(".//a/@data-product_sku").string()
        revs_count = prod.xpath(".//div/@data-number-of-reviews").string()
        if revs_count and int(revs_count) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, sku=sku))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["ssid"]
    product.sku = context["sku"].replace('data-product_sku', '')
    product.category = context["cat"]

    ean = data.xpath("//tr[contains(@class, '--attribute_ean')]/td//text()").string(multiple=True)
    if ean:
        product.add_property(type="id.ean", value=ean)

    revs = data.xpath("//div[@class='jdgm-rev-widg__reviews']/div")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = context["url"]
        review.title = rev.xpath(".//b[@class='jdgm-rev__title']/text()").string()
        review.ssid = rev.xpath("@data-review-id").string()

        is_verified = rev.xpath("@data-verified-buyer").string()
        if is_verified:
            if is_verified == "true":
                review.add_property(type='is_verified_buyer', value=True)
            else:
                review.add_property(type='is_verified_buyer', value=False)

        date = rev.xpath(".//span[contains(@class, 'jdgm-rev__timestamp')]/@data-content").string()
        if date:
            review.date = date.split(' ')[0]

        author_name = rev.xpath(".//span[@class='jdgm-rev__author']/text()").string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = data.xpath(".//span/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)