from agent import *
from models.products import *
import simplejson


XCAT = ['Weber® Expert Tips', '2021']


def run(context, session):
    session.queue(Request('https://www.wowbbq.co.uk/', use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//li[contains(@class,'li-level-1')]/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        if not name in XCAT:
            cats2 = cat.xpath("following-sibling::ul//li[contains(@class,'li-level-2')]/a")
            for cat2 in cats2:
                name2 = cat2.xpath("text()").string()
                url2 = str(cat2.xpath("@href").string()) + "/page=viewall"
                cats3 = cat2.xpath("following-sibling::ul/li/a")
                if cats3:
                    for cat3 in cats3:
                        name3 = cat3.xpath("text()").string()
                        url3 = str(cat3.xpath("@href").string()) + "/page=viewall"
                        session.queue(Request(url3), process_category, dict(cat=str(name)+'|'+str(name2)+'|'+ str(name3)))
                else:
                    session.queue(Request(url2), process_category, dict(cat=str(name)+'|'+str(name2)))


def process_category(data, context, session):
    prods = data.xpath("//div[@class='product']")
    for prod in prods:
        name = prod.xpath(".//h5/text()").string()
        url = prod.xpath(".//a/@href").string()
        session.queue(Request(url, use="curl"), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.category = context["cat"]
    product.url = context["url"]
    product.manufacturer = "Weber"

    ean = data.xpath("//b[contains(.,'Barcode')]/text()").string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean.replace('Barcode: ', '')))

    sku = data.xpath("//input[@name='sku']/@value").string()
    if sku:
        product.ssid = sku.replace('WEB', '')
        product.sku = product.ssid
        reviewsurl = "https://api.reviews.co.uk/product/review?store=wowbbq&sku=" + str(sku) + "&mpn=&lookup=&product_group=&minRating=4&tag=&sort=undefined&per_page=100&page=1"
        session.do(Request(reviewsurl, use="curl"), process_reviews, dict(context, product=product, revspage=1))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context["product"]
    resp = simplejson.loads(data.content.replace('{}', ''))

    revscount = resp["reviews"]["total"]

    revs = resp["reviews"]["data"]

    for rev in revs:
        review = Review()
        review.date = str(rev["date_created"]).split(' ')[0]
        review.ssid = str(rev["product_review_id"])
        review.type = "user"
        review.url = product.url

        author = str(rev["reviewer"]["first_name"]) + " " + str(rev["reviewer"]["last_name"])
        authorssid = author + " " + review.ssid
        review.authors.append(Person(name=author, ssid=authorssid))

        if 'yes' in rev['reviewer']['verified_buyer']:
            review.add_property(type='is_verified_buyer', value=True)

        grade = rev["rating"]
        review.grades.append(Grade(type="overall", value=grade, best=5))

        excerpt = rev["review"]
        review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

        if excerpt:
            product.reviews.append(review)
            revscount -= 1

    if revscount == 0:
        return

    revsid = resp.get("product_review_id", context["revsid"])
    revspage = context["revspage"] + 1

    reviewsurl = "https://api.reviews.co.uk/product/review?store=wowbbq&sku=" + str(product.ssid) + "&mpn=&lookup=&product_group=&minRating=4&tag=&sort=undefined&per_page=100&page=" + str(revspage)
    session.do(Request(reviewsurl, use="curl"), process_reviews, dict(context, product=product, revscount=revscount, revspage=revspage, revsid=revsid))
