import simplejson

from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.softonic.com.br'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[.//span[contains(text(), "Apps")]]/ul/li[ul/li]')
    for cat in cats:
        name = cat.xpath('span/text()').string()

        subcats = cat.xpath('.//li[not(div)]/a[contains(@class, "js-menu-categories-item")]')
        for subcat in subcats:
            subcat_name = subcat.xpath('text()').string()
            url = subcat.xpath('@href').string() + ':data'
            session.queue(Request(url), process_category, dict(cat=name + "|" + subcat_name))


def process_category(data, context, session):
    prods = data.xpath('//li[@class="apps-list__item"]')
    for prod in prods:
        name = prod.xpath('.//h2[@class="app-info__name"]//text()').string()
        url = prod.xpath('.//a[contains(@class, "app-info")]/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath('//li[@class="s-pagination__number s-pagination__number--current"]/following-sibling::li/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))


def process_product(data, context, session):
    prod_json = data.xpath('//script[contains(text(), "applicationCategory")]//text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
    else:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = prod_json.get('author', {}).get('name')
    product.ssid = data.xpath('//meta[@name="appId"]/@content').string()

    review = Review()
    review.type = "pro"
    review.url = product.url
    review.date = prod_json.get('dateModified')

    author = prod_json.get('review', {}).get('author', {}).get('name')
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = prod_json.get('review', {}).get('positiveNotes', {}).get('itemListElement', {})
    for pro in pros:
        pro = pro.get('name')
        if pro:
            review.add_property(type='pros', value=pro)

    cons = prod_json.get('review', {}).get('negativeNotes', {}).get('itemListElement', {})
    for con in cons:
        con = con.get('name')
        if con:
            review.add_property(type='cons', value=con)

    grade_overall = data.xpath('//li[@class="app-header__item app-header__item--double"]//p/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    excerpt = prod_json.get('review', {}).get('reviewBody')
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
        review.ssid = product.ssid
        product.reviews.append(review)
        session.emit(product)
