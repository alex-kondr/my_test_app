from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mattenlager.de/', use="curl", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//div[@class="mobile-nav-content"]/ul/li')
    for cat1 in cats1:
        name1 = cat1.xpath('span//a/text()').string()
        cats2 = cat1.xpath('ul/li//a')
        for cat2 in cats2:
            name2 = cat2.xpath('text()').string()
            url = cat2.xpath('@href').string()
            session.queue(Request(url+'?view=view-48', use="curl", force_charset='utf-8'), process_prodlist, dict(cat=name1+'|'+name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@class="productitem--link"]/@href').strings()
    for prod in prods:
        prod_id = prod.split('products/')[-1]
        url = 'https://www.mattenlager.de/products/' + prod_id
        session.queue(Request(url, use="curl", force_charset='utf-8'), process_product, dict(context, url=url))

    # No next page


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[@class="product-title"]//span/text()').string()
    product.manufacturer = 'Mattenlager'
    product.url = context['url']
    product.category = context['cat']
    product.ssid = data.xpath('//div[@id="shopify-product-reviews"]/@data-id').string()

    prod_json = data.xpath('''//script[contains(., '"@type": "Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('sku')

        ean = prod_json.get('mpn')
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

    revs = data.xpath('//span[@class="spr-summary-caption"][not(contains(., "Bisher keine"))]//text()').string(multiple=True)
    if revs:
        revs_cnt = int(revs.split('auf ')[-1].split()[0])
        if revs_cnt > 0:
            revs_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{pid}&page=1&product_id={pid}&shop=mattenlager.myshopify.com'.format(pid=product.ssid)
            session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    html_content = data.content.split(product.ssid, 1)[-1].strip('()')
    json = simplejson.loads(html_content)
    resp = json.get('reviews')
    revs_html = data.parse_fragment(resp)

    revs = revs_html.xpath('//div[@class="spr-review"]')
    for rev in revs:
        review = Review()
        review.url = product.url
        review.title = rev.xpath('.//h3[@class="spr-review-header-title"]/text()').string()
        review.type = "user"
        review.ssid = rev.xpath('@id').string().split('-')[-1]

        author_date = rev.xpath('.//span[@class="spr-review-header-byline"]//text()').string(multiple=True)
        if author_date:
            author_date = author_date.split(' am ')
            author_name = author_date[0]
            review.authors.append(Person(name=author_name, ssid=author_name))
            review.date = author_date[1]

        grade_overall = rev.xpath('.//span[@class="spr-starratings spr-review-header-starratings"]/@aria-label').string()
        if grade_overall:
            grade_overall = grade_overall.split('of ')[0]
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//p[@class="spr-review-content-body"]/text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            product.reviews.append(review)

    next_url = revs_html.xpath('.//span[@class="spr-pagination-next"]').string()
    if next_url:
        next_page = context.get('page', 1) + 1
        next_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{pid}&page={}&product_id={pid}&shop=mattenlager.myshopify.com'.format(next_page, pid=product.ssid)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page))
