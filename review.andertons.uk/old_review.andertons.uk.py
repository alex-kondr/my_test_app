from agent import *
from models.products import *


XCAT = ["Offers", "Brands", "Customer Service", "Corporate Info"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.andertons.co.uk/sitemap'), process_catlist, dict())


def process_catlist(data, context, session):
    cats1 = data.xpath("//div[@class='dtb-sitemap__segment-content']/div")
    for cat1 in cats1:
        cat1_name = cat1.xpath('h2/a[@aria-level="2"]/text()').string()
        if not cat1_name:
            cat1_name = cat1.xpath("h2/text()").string()
        if cat1_name in XCAT:
            continue
        url = cat1.xpath('h2//a[@aria-level="2"]/@href').string()
        cats2 = cat1.xpath("ul/li")
        if not cats2:
            session.queue(Request(url), process_prodlist, dict(cat=cat1_name))
        for cat2 in cats2:
            cat2_name = cat2.xpath("a/text()").string()
            url = cat2.xpath("a/@href").string()
            cats3 = cat2.xpath(".//li/a")
            if not cats3:
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))
            for cat3 in cats3:
                cat3_name = cat3.xpath("text()").string()
                url = cat3.xpath("@href").string()
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="c-product-grid"]//div[@class="o-tile"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="o-tile__row o-tile__title no-border"]/h4/text()').string()
        url = prod.xpath('.//a[@class="o-tile__link"]/@href').string()

        revs = prod.xpath('.//div[@class="o-tile__row o-tile__reviews"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next= data.xpath("(//li[@class='o-pagination__item is-active'])[1]/following-sibling::li[1]/a/text()")
    if next and next.string()!="Next":
        if not "?pageNumber=" in data.response_url:
            next_page = data.response_url+"?pageNumber="+next.string()
        else:
            next_page = data.response_url.split("?pageNumber=")[0]+"?pageNumber="+next.string()

        if next_page:
            session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']

    sku = data.xpath('//p[@class="o-part-number" and contains(text(), "SKU:")]/text()').string()
    if sku:
        product.sku = sku.replace('SKU:', '').strip()
        product.ssid = product.sku
    else:
        product.ssid = product.url.split('/')[-1]

    revs = data.xpath('//div[@class="o-customer-review"]')
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.date = rev.xpath('.//div[@class="o-customer-review__info"]//span[contains(@class, "review__date")]/text()').string()

        author_name = rev.xpath('.//div[@class="o-customer-review__info"]/p[@class="o-customer-review__name"]/span[not(@class)]/text()').string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath('.//div[@class="o-review-stars"]/@title').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.xpath('.//p[@class="o-customer-review__rating"]/span')
        if grades:
            for grade in grades:
                name_value = grade.xpath("text()").string()
                if name_value:
                   name = name_value.split(" ")[0]
                   value = float(name_value.split(" ")[1])
                   review.grades.append(Grade(name=name, value=value, best=5.0))
                else:
                    continue

        excerpt = rev.xpath('text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest()
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
