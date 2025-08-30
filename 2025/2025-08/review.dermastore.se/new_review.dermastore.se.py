from agent import *
from models.products import *


XCAT = ["Varumärken"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://dermastore.se/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[li[@class="has_children"]]/li[not(@class)]/a')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name, cat_url=url))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//li[div[@class="filter_title" and contains(text(), "Kategori")]]/div/ul/li')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath("text()").string()
        cat_id = sub_cat.xpath("@id").string()
        url = context["cat_url"] + "?limit=300&forcefiltersupdate=true&checkedfilters%5B%5D=" + cat_id
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="list-item"]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//h3[@class="wname"]//text()').string()
        product.url = prod.xpath('.//h3[@class="wname"]/a/@href').string().split('?')[0]
        product.ssid = prod.xpath(".//a[contains(@onclick, 'addToWishList')]/@onclick").string().split("'")[-2]
        product.sku = product.ssid
        product.category = context["cat"]

        revs = prod.xpath('.//span/@data-original-title')
        if revs:
            revs_url = "https://dermastore.se/index.php?route=product/product/review&product_id=" + product.ssid + "&page=1"
            session.queue(Request(revs_url), process_reviews, dict(product=product))

    next_page = data.xpath('//link[@rel="next"]/@href').string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context["product"]

    revs = data.xpath("//tbody/tr")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.xpath("td/i/text()").string()
        if date:
            review.date = date.replace('skrev', '').strip()

        grade_overall = rev.xpath("td/span[contains(@class, 'rating')]/@class").string()
        if grade_overall:
            grade_overall = float(grade_overall.split('rating')[-1])
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        author = rev.xpath("td[@class='user']/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath("td[@class='text']//text()").string(multiple=True)
        if excerpt and len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_page = data.xpath("//a[text()='>']/@href").string()
    if next_page:
        session.do(Request(next_page), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
