from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.digixo.com/', use="curl", force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath("//li[@class='cbp-hrtitle']")
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string(multiple=True)

        cats2 = cat1.xpath('.//div[@class="cbp-hrsub-inner"]/div')
        for cat2 in cats2:
            name2 = cat2.xpath('h4//text()').string(multiple=True)

            cats3 = cat2.xpath('ul//a')
            for cat3 in cats3:
                name3 = cat3.xpath('text()').string(multiple=True)
                url = cat3.xpath('@href').string()
                session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(cat=name1+'|'+name2+'|'+name3))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-txt")][//i[contains(@class, "fa-star")]]')
    for prod in prods:
        brand = prod.xpath('div[@class="brandname"]/text()').string()
        name = prod.xpath('div/span[@class="entityname"]/text()').string()
        url = prod.xpath(".//a/@href").string()
        session.queue(Request(url, use="curl", force_charset='utf-8', max_age=0), process_product, dict(context, name=name, brand=brand, url=url))

    next_url = data.xpath('//a[@title="Aller à la page suivante"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.manufacturer = context['brand']
    product.category = context["cat"]
    product.url = context["url"]
    product.ssid = product.url.split("/p")[-1].split('-')[0]

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.properties.append(ProductProperty(type="id.ean", value=ean))

    revs = data.xpath("//div[contains(@class, 'vignette_review')]")
    for rev in revs:
        review = Review()
        review.title = rev.xpath('.//h6[contains(@data-id, "review_titre")]/span/text()').string()
        review.url = product.url
        review.type = "user"

        author = rev.xpath('.//span[@class="review_pseudo"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('.//p[contains(@data-id, "review_comment_pos")]/span/text()').string()
        if pros:
            pros = pros.split('. ')
            for pro in pros:
                review.properties.append(ReviewProperty(type='pros', value=pro))

        cons = rev.xpath('.//p[contains(@data-id, "review_comment_neg")]/span/text()').string()
        if cons:
            cons = cons.split('. ')
            for con in cons:
                review.properties.append(ReviewProperty(type='cons', value=con))

        grade_overall = rev.xpath('.//span[@class="review_note_rank"]/text()').string()
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//p[contains(@data-id, "review_comment") and not(contains(@data-id, "pos") or contains(@data-id, "neg"))]/span/text()').string()
        if excerpt:
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next page
