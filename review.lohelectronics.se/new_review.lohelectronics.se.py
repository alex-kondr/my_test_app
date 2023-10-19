from agent import *
from models.products import *


XCAT = ["Fyndhörnan"]


def run(context, session):
    session.queue(Request("https://www.lohelectronics.se/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//ul[contains(@class, 'megamenu')]/li[(contains(@class, 'with-sub-menu') or @class='fyndmenu') and not(contains(@class, 'pull-right'))][position() < 6]")
    for cat in cats:
        name = cat.xpath("a/span//text()").string()

        if name not in XCAT:
            sub_cats = cat.xpath(".//div[@class='menu']/ul/li")
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath("a/text()").string()

                sub_cats1 = sub_cat.xpath("ul/li/a[not(regexp:test(@href, '(wiki|hsupport).lohelectronics.se', 'i'))]")
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath(".//text()").string()
                    url = sub_cat1.xpath("@href").string()
                    session.queue(Request(url + "?sort=rating&order=DESC&limit=100"), process_prodlist, dict(cat=name + "|" + sub_name + "|" + sub_name1))

                else:
                    url = sub_cat.xpath("a/@href").string()
                    session.queue(Request(url + "?sort=rating&order=DESC&limit=100"), process_prodlist, dict(cat=name + "|" + sub_name))

            else:
                url = cat.xpath("a/@href").string()
                session.queue(Request(url + "?sort=rating&order=DESC&limit=100"), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='item well']")
    for prod in prods:
        name = prod.xpath(".//span[@class='product-name']/a/text()").string()
        manufacturer = prod.xpath(".//div[@class='details-area']//p/a/i/text()").string()
        mpn = prod.xpath(".//div[@class='details-area']//p/text()").string(multiple=True)
        url = prod.xpath(".//span[@class='product-name']/a/@href").string()

        product_id = prod.xpath(".//a[contains(@class, 'btn-wishlist')]/@onclick").string().split("'", 1)[-1].replace("');", "")
        revs_url = "https://www.lohelectronics.se/product/product/review?product_id=" + product_id + "&page=1"

        rating = prod.xpath(".//div[contains(@class, 'star-rating')]")
        if rating:
            options = "--compressed -H 'X-Requested-With: XMLHttpRequest'"
            session.queue(Request(revs_url, use='curl', options=options, max_age=0, force_charset='utf-8'), process_product, dict(context, name=name, url=url, manufacturer=manufacturer, mpn=mpn))
        else:
            return

    next_url = data.xpath("//a[i[@class='fas fa-chevron-right'] and not(i[@style])]").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
        product = Product()
        product.name = context["name"]
        product.url = context["url"].split("?")[0]
        product.ssid = product.url.split('/')[-1].split('?')[0]
        product.category = context["cat"]
        product.manufacturer = context["manufacturer"]

        if context["mpn"]:
            mpn = context["mpn"].split(' -')[0].strip()
            product.properties.append(ProductProperty(type="id.manufacturer", value=mpn))

        context["product"] = product
        process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context["product"]

    revs = data.xpath("//div[@class='review-list']")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath("div[@class='author']/span/text()").string()

        grade_overall = rev.xpath("count(div[@class='rating']/i[@class='fa fa-star active'])")
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        author = rev.xpath("div[@class='author']/b/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        excerpt = rev.xpath("div[@class='text']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_page = data.xpath("//li[@class='active']/following-sibling::li[1]/a/@href").string()
    if next_page:
        session.queue(Request(next_page), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
