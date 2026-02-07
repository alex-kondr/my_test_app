from agent import *
from models.products import *
import simplejson


XCAT = ['New', 'Brands', 'Sale %', 'Inspiration']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.wardow.com/en/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "menu-list")]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name not in XCAT:
            subcats = cat.xpath('.//li[div/a/span[contains(text(), "Categories")]]/div/ul/li/a[not(contains(., "Show all"))]')
            for subcat in subcats:
                subcat_name = subcat.xpath('.//text()').string(multiple=True)
                url = subcat.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name+'|'+subcat_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="product-card__link"]')
    for prod in prods:
        name = prod.xpath('.//text()').string(multiple=True)
        url = 'https://www.wardow.com/en/products/' + prod.xpath('@href').string().split('/')[-1]
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-yotpo-product-id').string()
    product.sku = data.xpath('//strong[contains(text(), "Product No.:")]/following-sibling::text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//a[@class="product-vendor"]/text()').string()

    mpn = data.xpath('//strong[contains(text(), "Model number:")]/following-sibling::text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    prod_json = data.xpath("""//script[contains(., '"@type":"Product"')]/text()""").string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 0:
            product.add_property(type='id.ean', value=ean)

    revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/juPydjP7F5lNKZqAAkBS8XjnFJaiWnVEaQq9xmxN/product/{}/reviews?page=1&perPage=5'.format(product.ssid)
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        if rev.get('language') != 'en' or rev.get('syndicationData'):
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('displayName')
        author_ssid = rev.get('user', {}).get('userId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('score')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('votesUp')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('votesDown')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        is_verified_buyer = rev.get('verifiedBuyer')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('pagination', {}).get('total', 0)
    offset = context.get('offset', 0) + 5
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://api-cdn.yotpo.com/v3/storefront/store/juPydjP7F5lNKZqAAkBS8XjnFJaiWnVEaQq9xmxN/product/{ssid}/reviews?page={page}&perPage=5'.format(ssid=product.ssid, page=next_page)
        session.do(Request(revs_url), process_reviews, dict(product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
