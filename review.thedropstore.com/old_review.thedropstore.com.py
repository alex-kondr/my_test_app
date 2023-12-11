from agent import *
from models.products import *
import simplejson


XCAT = ['Shop All', 'Shop all']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://thedropstore.com/', use="curl"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//li[@class='nav-bar__item']//a[@class='nav-dropdown__link link']")
    for cat in cats:
        cat_name = cat.xpath(".//text()").string(multiple=True)
        url = cat.xpath("@href").string()
        if url and cat_name and (cat_name not in XCAT):
            session.queue(Request(url, use="curl"), process_prodlist, dict(cat=cat_name))


def process_prodlist(data, context, session):
    for prod in data.xpath("//div[contains(@class, 'product-item product-item--vertical')]"):
        product = Product()
        product.category = context['cat']
        product.name = prod.xpath(".//a[@class='product-item__title text--strong link']/text()").string()
        product.url = prod.xpath(".//a[@class='product-item__title text--strong link']/@href").string()
        product.ssid = prod.xpath(".//a[@class='product-item__reviews-badge link']/span/@data-id").string()

        rev_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback" + product.ssid + "&page=1&product_id=" + product.ssid + "&shop=thedropstore-com.myshopify.com"
        session.do(Request(rev_url, use="curl", force_charset='utf-8'), process_reviews, dict(context, product=product))

        if product.reviews:
            session.emit(product)

    next_url = data.xpath("//a[@class='pagination__next link']/@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl"), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    response = data.xpath("//body/text()").string().strip()
    rep1 = 'productCallback' + product.ssid + '('
    rep2 = 'paginateCallback' + product.ssid + '('
    if rep1 in data.content:
        response = response[:-1].split(rep1)[-1]
    elif rep2 in data.content:
        response = response[:-1].split(rep2)[-1]

    revs_html = simplejson.loads(response).get('reviews').replace('\\"', '')
    revs_html = data.parse_fragment(revs_html)
    if not revs_html:
        return

    revs = revs_html.xpath("//div[@class='spr-review']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath("@id").string().split('-')[-1]
        review.title = rev.xpath(".//h3/text()").string()
        review.date = rev.xpath('.//span[@class="spr-review-header-byline"]/strong[2]/text()').string()

        author = rev.xpath('.//span[@class="spr-review-header-byline"]/strong[1]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        rating = rev.xpath(".//span[contains(@class,'spr-starratings')]/@aria-label").string().split('of')[0].strip()
        if rating:
            rating = rating.split('of')[0].strip()
            review.grades.append(Grade(name='Overall', type='overall', value=float(rating), best=5.0))

        excerpt = rev.xpath(".//p[@class='spr-review-content-body']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('\n', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    next_page = revs_html.xpath("//span[@class='spr-pagination-next']/a/@data-page").string()
    if next_page:
        next_url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback{ssid}&page={next_page}&product_id={ssid}&shop=thedropstore-com.myshopify.com".format(ssid=product.ssid, next_page=next_page)
        session.do(Request(next_url, use="curl"), process_reviews, dict(product=product))
