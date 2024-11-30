from agent import *
from models.products import *
import simplejson
import HTMLParser
import re


XCAT = ['WBY']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://www.miekofishing.se/', use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="li0 has-ul"]')
    for cat in cats:
        name = cat.xpath('(a|span)//text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//li[contains(@class, "li1")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('(a|span)//text()').string(multiple=True)

                sub_cats1 = sub_cat.xpath('.//li[contains(@class, "li2")]')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('(a|span)/text()').string()
                    url = sub_cat1.xpath('a/@href').string()

                    if sub_name1 and url:
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "product-title")]/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = context['cat'].replace('|Övriga tillbehör', '').replace('|Övrigt', '').replace('|Övriga Spinnare', '').replace('|Övriga skeddrag', '')
    product.sku = data.xpath('//input[@name="id_product"]/@value').string()
    product.manufacturer = data.xpath('//tr[@class="product-brand"]/td[@class="value"]//text()').string(multiple=True)

    mpn = data.xpath('//tr[@class="product-reference"]/td[@class="value"]//text()').string(multiple=True)
    if mpn and re.search(r'^[\d\-\.]+$', mpn):
        product.add_property(type="id.manufacturer", value=mpn)

    ean = data.xpath('//tr[contains(., "ean13")]/td[@class="value"]//text()').string(multiple=True)
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath('//small[contains(., "recensioner)")]')
    if revs_cnt:
        revs_url = 'https://www.miekofishing.se/module/productcomments/ListComments?id_product={sku}&page=1'.format(sku=product.sku)
        session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    h = HTMLParser.HTMLParser()
    revs_data = simplejson.loads(data.content)

    revs = revs_data.get('comments', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('date_add')
        if date:
            review.date = date.split()[0]

        author = rev.get('customer_name')
        if author:
            author = h.unescape(author)
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('grade')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('usefulness')
        if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_total = rev.get('total_usefulness')
        if hlp_total and hlp_total.isdigit() and int(hlp_total) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_total) - int(hlp_yes))

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt:
            review.title = h.unescape(title).replace('\r\n', ' ').replace('  ', ' ').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = h.unescape(excerpt).replace('\r\n', ' ').replace('  ', ' ').strip()
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.get('id_product_comment')
            if ssid:
                review.ssid = str(ssid)
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    revs_cnt = revs_data.get('comments_nb', 0)
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.miekofishing.se/module/productcomments/ListComments?id_product={sku}&page={page}'.format(sku=product.sku, page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
