from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.avedastore.ie/', force_charset='utf-8', use='curl'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats1 = data.xpath('//li[contains(@class, "site-nav")][not(contains(@class, "grandchild"))]')
    for cat1 in cats1:
        name1 = cat1.xpath('a/text()').string().strip()

        cats2 = cat1.xpath('.//li[a[contains(., "Category")]]/ul//a')
        for cat2 in cats2:
            name2 = cat2.xpath('text()').string()
            url = cat2.xpath('@href').string()

            if 'All ' not in name2:
                session.queue(Request(url, force_charset='utf-8', use='curl'), process_prodlist, dict(cat=name1 + '|' + name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "grid-item small--one-half")]')
    for prod in prods:
        name = prod.xpath('p/text()').string()
        url = prod.xpath('a/@href').string()
        ssid = prod.xpath('span/@data-id').string()
        if name and url and ssid:
            session.queue(Request(url, force_charset='utf-8', use='curl'), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.manufacturer = 'Aveda'
    product.ssid = context['ssid']
    product.sku = data.xpath('//option[@data-sku]/@data-sku').string()

    ean = data.xpath('//script[@id="ProductJson-product-template"]/text()').string()
    if ean:
        ean = ean.split('"barcode":"', 1)[-1].split('",')[0]
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=ean))

    revs = data.xpath('//span[@class="spr-summary-actions-togglereviews"]//text()').string()
    if revs:
        revs_cnt = int(revs.split('on ')[-1].split()[0])
        if revs_cnt > 0 and product.ssid:
            rev_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{}&page=1&product_id={}&shop=avedaireland.myshopify.com'.format(product.ssid, product.ssid)
            options = """-H "authority: productreviews.shopifycdn.com" -H "accept: */*" -H "accept-language: uk,en;q=0.9,en-GB;q=0.8,en-US;q=0.7" -H "cache-control: no-cache" -H "pragma: no-cache" -H "referer: https://www.avedastore.ie/" -H "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81" --compressed"""
            session.do(Request(rev_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(product=product))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    html_content = data.xpath('//text()').string()
    if not html_content:
        return

    html_content = html_content.split(product.ssid, 1)[-1].strip('()')

    json = simplejson.loads(html_content)
    resp = json.get('reviews')
    revs_html = data.parse_fragment(resp)

    revs = revs_html.xpath('//div[@class="spr-review"]')
    for rev in revs:
        review = Review()
        review.product = product.name
        review.url = product.url
        review.title = rev.xpath('.//h3[@class="spr-review-header-title"]/text()').string()
        review.type = "user"
        review.ssid = rev.xpath('@id').string().split('-')[-1]

        date = rev.xpath('.//span[@class="spr-review-header-byline"]//text()').string(multiple=True)
        if date:
            review.date = date.split('on ')[-1]

        author = rev.xpath('.//span[@class="spr-review-header-byline"]//text()').string(multiple=True)
        if author:
            author = author.split('on ')[0]
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="spr-starratings spr-review-header-starratings"]/@aria-label').string()
        if grade_overall:
            value = grade_overall.split('of ')[0]
            review.grades.append(Grade(type="overall", value=float(value), best=5.0))

        excerpt = rev.xpath('.//p[@class="spr-review-content-body"]/text()').string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

            product.reviews.append(review)

    next_url = revs_html.xpath('.//span[@class="spr-pagination-next"]').string()
    if next_url:
        next_page = context.get('page', 1) + 1
        rev_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{}&page={}&product_id={}&shop=avedaireland.myshopify.com'.format(product.ssid, next_page, product.ssid)
        options = """-H "authority: productreviews.shopifycdn.com" -H "accept: */*" -H "accept-language: uk,en;q=0.9,en-GB;q=0.8,en-US;q=0.7" -H "cache-control: no-cache" -H "pragma: no-cache" -H "referer: https://www.avedastore.ie/" -H "user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81" --compressed"""
        session.do(Request(rev_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_reviews, dict(context, product=product, page=next_page))
