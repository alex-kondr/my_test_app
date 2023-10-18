from agent import *
from models.products import *

import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.moglix.com/all-categories'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="all-cate-section pad-15"]')
    for cat in cats:
        name = cat.xpath('h3[@class="red-txt"]/text()').string()

        sub_cats = cat.xpath('.//div[@class="cate-type"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//strong[@data-_ngcontent-sc230]/text()').string()

            sub_cats1 = sub_cat.xpath('a[not(strong)]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string()
                url = sub_cat1.xpath('@href').string()
                ###########################
                session.queue(Request(url), process_subcatlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_subcatlist(data, context, session):
    subcats = data.xpath("//div[@class='allCategorySlide']")
    for subcat in subcats:
        name = subcat.xpath("p/text()").string()
        url = subcat.xpath("a/@href").string()
        session.queue(Request(url, use="curl", force_charset="utf-8"), process_prodlist, dict(cat=context["cat"]+'|'+name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[contains(@class, 'row prod_list')]/div")
    for prod in prods:
        name = prod.xpath("a/@title").string()
        url = prod.xpath("a/@href").string()

        revs_count = prod.xpath(".//span[contains(@class, 'ratingCount')]")
        if revs_count:
            session.queue(Request(url, use="curl", force_charset="utf-8"), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset="utf-8"), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = context["url"].split('/')[-1]
    product.category = context["cat"]
    product.manufacturer = data.xpath("//h3[@id='product-spec']/following-sibling::div[1]//table/tr/td[contains(text(), 'Brand')]/following-sibling::td//text()").string()

    mpn = data.xpath("//h3[@id='product-spec']/following-sibling::div[1]//table/tr/td[contains(text(), 'Item Code')]/following-sibling::td//text()").string()
    if mpn:
        product.add_property(type="id.manufacturer", value=mpn)
        product.ssid = mpn

    revs_info = data.xpath("//script[@id='online-web-state']/text()").string()
    if not "reviewList" in revs_info:
        return

    revs_info = revs_info.replace("&q;", "\"")
    revs_info = '{"reviews"' + revs_info.split('"RRD"')[-1].split('"RRDC"')[0][:-1].replace('\n', '') + '}'
    revs_info = simplejson.loads(revs_info)

    revs = revs_info["reviews"]["reviewList"]
    for rev in revs:
        review = Review()
        review.type = "user"
        review.title = rev["review_subject"]
        review.ssid = rev["review_id"]["uuid"]
        review.date = rev["date"]
        review.url = product.url

        overall = int(rev["rating"])
        if overall > 5:
            overall = 5
        review.grades.append(Grade(type="overall", value=overall, best=5))

        author = rev["user_name"]
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev["is_approved"]
        review.add_property(type="is_verified_buyer", value=is_verified)

        excerpt = rev["review_text"]
        if excerpt:
            excerpt = excerpt.strip()

            review.add_property(type="excerpt", value=excerpt)
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
