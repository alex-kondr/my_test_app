from agent import *
from models.products import *
import simplejson


X_SUBCATS = ["Nursery Sets", "Kids' Bedroom Sets", 'All Strollers', 'Shop by Character']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.deltachildren.com/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('(//h2[@class="navigation-mobile__title pb1 mt0 mb3"]/following-sibling::ul)[1]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string()
        url = cat.xpath('a/@href').string()

        subcats = cat.xpath('.//div[@class="navigation-mobile__nav-subitem navigation-mobile__nav-subitem--mega"]')
        if subcats:
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string(multiple=True)
                url = subcat.xpath('a/@href').string()
                if subcat_name not in X_SUBCATS:
                    session.queue(Request(url), process_prodlist, dict(cat=name + "|" + subcat_name, url=url))
        else:
            session.queue(Request(url), process_prodlist, dict(cat=name, url=url))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="v2-container"]/a')
    if not prods:
        prods = data.xpath('//div[contains(@class, "category-box")]/a')

    if not prods:
        process_product(data, context, session)
        return

    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//a[span[contains(text(), "Next page")]]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath('//script[contains(text(), \'"@type": "Product"\')]//text()').string())

    product = Product()
    product.name = data.xpath('//h1[@class="product__title"]//text()').string()
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = "Delta Children"
    product.ssid = data.xpath('//span[@class="shopify-product-reviews-badge"]/@data-id').string()

    mpn = data.xpath('//div[@class="product__variant-sku-ups"]/span[@id="display_sku"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[@class="product__variant-sku-ups"]/span[@id="display_upc"]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_cnt = prod_json.get('aggregateRating', {}).get('ratingCount')
    if revs_cnt and int(revs_cnt) > 0:
        revs_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews/product?product_id={ssid}&version=v4&shop=deltachildrenstore.myshopify.com".format(ssid=product.ssid)
        session.do(Request(revs_url, force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    new_data = data.parse_fragment(revs_json['reviews'])

    revs = new_data.xpath('//div[@class="spr-review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        title = rev.xpath('.//h3//text()').string()
        if title:
            review.title = title.encode().decode()

        ssid = rev.xpath('@id').string()
        if ssid:
            review.ssid = ssid.split('view-')[-1]

        rev_content = rev.xpath('.//span[@class="spr-review-header-byline"]//text()').string(multiple=True)
        if rev_content:
            review.date = rev_content.split(' on ')[-1]

            author = rev_content.split(' on ')[0]
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="spr-starratings spr-review-header-starratings"]/@aria-label').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(' of ')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath(".//p[@class='spr-review-content-body']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.encode().decode()
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page, loaded all revs
