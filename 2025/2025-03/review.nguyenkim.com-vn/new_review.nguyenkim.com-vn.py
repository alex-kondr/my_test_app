from agent import *
from models.products import *
import simplejson


XCAT = ['Dịch vụ', 'Hỗ trợ', 'Hệ thống siêu thị', 'Thông tin hữu ích', 'Bán hàng doanh nghiệp']


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
    session.queue(Request("https://www.nguyenkim.com"), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="menu-item"]//a')
    for cat in cats:
        name = cat.xpath('text()').string().strip()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_prodlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//a[@class="item"]')
    if subcats:
        for subcat in subcats:
            name = subcat.xpath('h4[@class="cate-title"]//text()').string()
            url = subcat.xpath('@href').string()
            session.queue(Request(url), process_catlist, dict(cat=context['cat'] + '|' + name))
    else:
        process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "categories-view")]/a[contains(@class, "product-render")]')
    for prod in prods:
        name = prod.xpath('@name').string()
        ssid = prod.xpath('@product-id').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.ssid
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        product.manufacturer = prod_json.get('brand', {}).get('name')

        mpn = prod_json.get('sku')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@class="post post-main"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().replace('post_', '')

        author = rev.xpath('.//div[@class="post_author-name"]/span//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[contains(@class, "post_stars")]/span//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//div[@class="post_btn btn-like"]/span//text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        excerpt = rev.xpath('div[@class="post_content"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@class="btn_viewMore cm-ajax"]').first()
    if next_url:
        url = next_url.xpath('@href').string() + '&' + next_url.xpath('@data-ca-target-id').string()
        session.do(Request(url, force_charset='utf-8'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
