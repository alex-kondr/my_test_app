from agent import *
from models.products import *
import simplejson


XCAT = ['Mats', 'hammer-home', 'Warranty Registration']


def run(context, session):
    session.queue(Request('https://hammeronline.in/', use='curl', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats1 = data.xpath("//div[@data-dropdown]")
    for cat1 in cats1:
        name1 = cat1.xpath('@data-dropdown').string()
        if name1 in XCAT:
            continue

        cats2 = cat1.xpath(".//div[@class='dropdown_column']")
        for cat2 in cats2:
            url = cat2.xpath(".//a/@href").string()
            name2 = cat2.xpath(".//p/text()").string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(context, cat=name2))

    cats1 = data.xpath("//li[contains(@class,'mobile-nav__item appear-animation')]/a")
    for cat1 in cats1:
        name = cat1.xpath('text()').string()
        if name in XCAT:
            continue
        url = cat1.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_category, dict(context, cat=name))


def process_category(data, context, session):
    prods = data.xpath("//div[@class='grid-product__content']")
    for prod in prods:
        name = prod.xpath(".//div[@class='grid-product__title grid-product__title--heading']/text()").string()
        url = prod.xpath("a/@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    revs = data.xpath("//span[@class='spr-summary-actions-togglereviews']//text()").string()
    if not revs:
        return  # No reviews

    product = Product()
    product.name = context['name']
    product.ssid = data.xpath("//div/@data-product-id").string()
    product.category = context['cat']
    product.url = context['url']
    product.manufacturer = 'Hammer'

    revs_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback4870528565384&page=1&product_id=' + str(product.ssid) + '&shop=hammer-audio.myshopify.com'
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=1))

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    resp_html = ''.join(data.content)
    resp_html = '{"' + resp_html.split('({"')[1][:-1]

    resp = simplejson.loads(resp_html)
    revs_json = resp['reviews']
    revs_html = data.parse_fragment(revs_json)

    revs = revs_html.xpath("//div[@class='spr-review']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//h3//text()").string()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//span[@class='spr-review-header-byline']/strong[2]//text()").string()

        author_name = rev.xpath(".//span[@class='spr-review-header-byline']/strong[1]//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath(".//span/@aria-label").string()
        if grade_overall:
            grade_overall = grade_overall.split(' of ')
            grade_overall[1] = grade_overall[1].split(' star')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall[0]), best=float(grade_overall[1])))

        excerpt = rev.xpath(".//p[@class='spr-review-content-body']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest()
            product.reviews.append(review)

    revs_count = int(revs_html.xpath("count(//div[@class='spr-review'])"))
    if revs_count >= 5:
        next_page = context['page'] + 1
        revs_url = 'https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback4870528565384&page=' + str(next_page) + '&product_id=' + str(product.ssid) + '&shop=hammer-audio.myshopify.com'
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, page=next_page))
