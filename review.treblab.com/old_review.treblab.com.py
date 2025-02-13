from agent import *
from models.products import *
import simplejson


XCAT = ['Home', 'Blog', 'Support']


def run(context, session):
    session.queue(Request('https://treblab.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@id='SiteNav']/li/a")
    for cat in cats:
        name = cat.xpath(".//text()").string(multiple=True)
        url = cat.xpath("@href").string()
        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[contains(@id, 'product-')]")
    for prod in prods:
        ssid = prod.xpath("@id").string().split('-')[-1]
        name = prod.xpath("h3[@class='product-card__title']/a/text()").string()
        url = prod.xpath("h3[@class='product-card__title']/a/@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url, ssid=ssid))


def process_product(data, context, session):
    if not data.xpath("//span[@class='spr-summary-caption']"):
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']

    url = "https://productreviews.shopifycdn.com/proxy/v4/reviews?callback=paginateCallback"
    session.do(Request(url + context['ssid'] + "&page=" + "1" + "&product_id=" + context['ssid'] + "&shop=treblab.myshopify.com", use='curl', force_charset='utf-8'), process_reviews, dict(context, product=product, revs_url=url, ssid_2=context["ssid"]))


def process_reviews(data, context, session):
    product = context['product']

    jstxt = data.content.split('({"')[-1].split('"})')[0].replace('\u003c', '<').replace('\u003e', '>')
    jstxt = '{"' + jstxt + '"}'
    reviews = simplejson.loads(jstxt)
    revs_html = data.parse_fragment(reviews['reviews'])

    revs = revs_html.xpath("//div[@class='spr-review']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.title = rev.xpath(".//h3[@class='spr-review-header-title']//text()").string()
        review.ssid = rev.xpath("@id").string().split('spr-review-')[-1]
        review.date = rev.xpath(".//div[@class='review-date']//text()").string()

        author = rev.xpath(".//div[@class='review-name']//text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        star = rev.xpath(".//span[@class='spr-starratings spr-review-header-starratings']//@aria-label").string().split(' of 5 stars')[0]
        if star:
            review.grades.append(Grade(type='overall', name='Rating', value=float(star), best=5.0))

        excerpt = rev.xpath(".//div[@class='spr-review-content']//p[@class='spr-review-content-body']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)
            product.reviews.append(review)

    ssid_2 = context["ssid_2"]
    if revs:
        page = context.get("page", 1) + 1
        session.do(Request(context["revs_url"] + ssid_2 + "&page=" + str(page) + "&product_id=" + ssid_2 + "&shop=treblab.myshopify.com", use='curl', force_charset='utf-8'), process_reviews, dict(context, product=product, page=page))
    elif product.reviews:
        session.emit(product)
