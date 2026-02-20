from agent import *
from models.products import *
import simplejson
from datetime import datetime
# import re


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.hudoteket.se/", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="produkt"]/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=name))


def process_category(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//ul[contains(@class, "cat-child-ul")]/li/a')
    for subcat in subcats:
        name = subcat.xpath('text()').string()
        url = subcat.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[.//h3]')
    for prod in prods:
        name = prod.xpath('.//h3/text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_product, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    prod_json = data.xpath('''//script[contains(., '"review":')]/text()''').string()
    if not prod_json:
        return

    prod_json = simplejson.loads(prod_json)

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-1]
    product.category = context["cat"]
    product.manufacturer = prod_json.get('brand', {}).get('name')

    mpn = prod_json.get('sku')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = prod_json.get('gtin8')
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=str(ean))

    revs = prod_json.get('review')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get("datePublished")
        if date:
            review.date = datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d")

        author = rev.get("author", {}).get("name")
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get("description")
        if excerpt and excerpt.strip():
            # excerpt = re.sub(r'&#\d+;?', '', excerpt).replace('<br>', '')

            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next page
