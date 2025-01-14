from agent import *
from models.products import *


XCAT = ["Begär intyg"]


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request("https://www.lohelectronics.se/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[contains(@class, 'megamenu')]/li[(contains(@class, 'with-sub-menu') or @class='fyndmenu') and not(contains(@class, 'pull-right'))][position() < 6]")
    for cat in cats:
        cat_name = cat.xpath("a/span//text()").string()
        url = cat.xpath("a/@href").string()
        cats2 = cat.xpath(".//div[@class='menu']/ul/li")
        if not cats2:
            session.queue(Request(url), process_prodlist, dict(cat=cat_name))
        for cat2 in cats2:
            cat2_name = cat_name + '|' + cat2.xpath("a/text()").string()
            cats3 = cat2.xpath("ul/li/a[not(regexp:test(@href, '(wiki|hsupport).lohelectronics.se', 'i'))]")
            for cat3 in cats3:
                url = cat3.xpath("@href").string()
                name = cat3.xpath(".//text()").string()
                if name not in XCAT:
                    name = cat2_name + '|' + name
                    session.queue(Request(url), process_prodlist, dict(cat=name))
            url = cat2.xpath("a/@href").string()
            session.queue(Request(url), process_prodlist, dict(cat=cat2_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='item well']")
    for prod in prods:
        name = prod.xpath(".//span[@class='product-name']/a/text()").string()
        url = prod.xpath(".//span[@class='product-name']/a/@href").string()
        brand = prod.xpath(".//div[@class='details-area']//p/a/i/text()").string()

        mpn = prod.xpath(".//div[@class='details-area']//p/text()").string(multiple=True)
        if mpn:
            mpn = mpn.split(' -')[0].strip()

        rating = prod.xpath(".//div[contains(@class, 'star-rating')]")
        if rating:
            prod_id = prod.xpath(".//a[contains(@class, 'btn-wishlist')]/@onclick").string().split("'")[1]
            revs_url = "https://www.lohelectronics.se/product/product/review?product_id=" + prod_id + "&page=1"
            session.queue(Request(revs_url), process_reviews, dict(context, name=name, url=url, brand=brand, mpn=mpn, revs_url=revs_url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context.get("product", Product())

    if not product.name:
        product.name = context["name"]
        product.url = context["url"]
        product.ssid = product.url.split('/')[-1]
        product.category = context["cat"]
        product.manufacturer = context["brand"]

        if context["mpn"]:
            product.properties.append(ProductProperty(type="id.manufacturer", value=context["mpn"]))

    revs = data.xpath("//div[@class='review-list']")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.date = rev.xpath("div[@class='author']/span/text()").string()
        review.url = context["revs_url"]

        overall = len(rev.xpath("div[@class='rating']/i[@class='fa fa-star active']"))
        if overall:
            review.grades.append(Grade(type="overall", value=overall, best=5))

        author = rev.xpath("div[@class='author']/b/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        review.ssid = product.ssid + '-' + hashlib.md5(review.date + author).hexdigest()

        excerpt = rev.xpath("div[@class='text']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)
            product.reviews.append(review)

    next_page = data.xpath("//li[@class='active']/following-sibling::li[1]/a/@href").string()
    if next_page:
        session.queue(Request(next_page), process_reviews, dict(product=product, revs_url=next_page))
    elif product.reviews:
        session.emit(product)
