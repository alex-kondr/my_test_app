from agent import *
from models.products import *


XCAT = ["Książki", "Ebooki i audiobooki", "Delikatesy", "Empikfoto.pl", "Empikbilety.pl", "PODCASTY", "PROMOCJE", "TOP"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.empik.com/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath("//div[@class='empikNav__menu-desktop']/div/ul/li[@class='nav-categories__separator']/following-sibling::li[not(@class='nav-categories__separator')]")
    for cat1 in cats1:
        cat1_name = cat1.xpath("a/@title").string()
        if cat1_name in XCAT:
            continue
        cats2 = cat1.xpath("div/div/ul/li/ul")
        for cat2 in cats2:
            cat2_name = cat2.xpath("li/a[contains(@class, 'nav-subcategories__link--header')]//text()").string()
            if not cat2_name:
                cat2_name = cat2.xpath("li/span[contains(@class, 'nav-subcategories__label--header')]//text()").string()
            url = cat2.xpath("li[1]/a/@href").string()
            if cat2_name in XCAT:
                continue
            cats3 = cat2.xpath("li/a[not(contains(@class, 'nav-subcategories__link--header'))][not(span[@style])]")
            if not cats3 and url:
                url += "?priceTo=&rateScore=5&rateScore=4&rateScore=3&rateScore=2&rateScore=1&resultsPP=60"
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))
            for cat3 in cats3:
                cat3_name = cat3.xpath(".//text()").string()
                url = cat3.xpath("@href").string() + "?priceTo=&rateScore=5&rateScore=4&rateScore=3&rateScore=2&rateScore=1&resultsPP=60"
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[contains(@class, 'ta-product-tile')]")
    for prod in prods:
        name = prod.xpath(".//a[img]/@title").string()
        url = prod.xpath(".//a[img]/@href").string()
        ssid = prod.xpath("@data-product-id").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = context.get("product", Product())
    if not product.name:
        product.name = context["name"].split('-')[0]
        product.url = context["url"]
        product.ssid = context["ssid"]
        product.sku = data.xpath("//tr[contains(@class, 'ta-attribute-row')]/td[contains(text(), 'Indeks:')]/following-sibling::td//text()").string(multiple=True)
        product.category = context["cat"]

        product.manufacturer = data.xpath("//a[@itemprop='author']/text()").string()
        if not product.manufacturer:
            product.manufacturer = data.xpath("//span[contains(@class, 'pDAuthorList')]/a/text()").string()
        if not product.manufacturer:
            product.manufacturer = context["name"].split('-')[-1]

    revs = data.xpath("//div[contains(@class, 'js-reviews-item')]")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.ssid = rev.xpath(".//div/@data-review").string()
        review.date = rev.xpath(".//strong[@class='nick']/preceding-sibling::text()").string(multiple=True).split(" o ")[0]
        review.url = product.url

        grade_overall = len(rev.xpath(".//i[@class='fa fa-fw fa-star active']"))
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5))

        author_name = rev.xpath(".//strong[@class='nick']/text()").string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        excerpt = rev.xpath("div[@class='productComments__itemDescription']/text()").string()
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    if revs:
        page = context.get("page", 0) + 1
        url = product.url + "/recenzje?page=" + str(page)
        session.do(Request(url), process_product, dict(product=product, page=page))

    elif product.reviews:
        session.emit(product)
