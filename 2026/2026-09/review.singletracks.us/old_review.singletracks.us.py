from agent import *
from models.products import *
import simplejson


XCAT = ["[ VIEW ALL BIKES ]"]


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.singletracks.com/', use='curl'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    print(data.content)
    cats = data.xpath("(//ul[@class='sub_menu']/li/a)[@title and not(@target='_blank')]")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        if name not in XCAT:
            session.queue(Request(url + "?sort_by=best-selling"), process_category, dict(cat=name, url=url))


def process_category(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath("//div[contains(@class, 'product-thumbnail')]")
    for prod in prods:
        name = prod.xpath("a/@title").string()
        url = prod.xpath("a/@href").string()
        product_id = prod.xpath(".//div[@id]/@id").string()
        rating = prod.xpath(".//span[@class='jdgm-prev-badge__text' and text() != ' No reviews ']")
        if not rating: # if this product doesn't have reviews: next product won't too
            return
        session.queue(Request(url), process_product, dict(context, name=name, url=url, product_id=product_id))

    next_url = data.xpath("//a[@class='next page-numbers']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.manufacturer = data.xpath("//a[@href[contains(., 'brand')]]//text()").string()

    url = "https://judge.me/reviews/reviews_for_widget?url=state-bicycle-co.myshopify.com&shop_domain=state-bicycle-co.myshopify.com&platform=shopify&page=1&per_page=10&product_id={0}"
    url = url.format(context["product_id"])
    session.do(Request(url), process_reviews, dict(url=url, product=product, page=1))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = context['product']
    info = simplejson.loads(data.content)
    data = data.parse_fragment(info["html"])

    revs = data.xpath("//div[@class='jdgm-rev jdgm-divider-top']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//span[contains(@class, 'jdgm-rev__timestamp')]/@data-content").string().split()[0]
        review.title = rev.xpath(".//b[@class='jdgm-rev__title']/text()").string()

        grade_overall = len(rev.xpath(".//span[@class='jdgm-rev__rating']/span"))
        review.grades.append(Grade(type='overall', value=int(grade_overall), best=5))

        author_name = rev.xpath(".//span[@class='jdgm-rev__author']/text()").first()
        review.authors.append(Person(name=author_name, ssid=author_name))


        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip()
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author_name else review.digest(excerpt)
                product.reviews.append(review)

    if revs:
        context["url"] = context["url"].replace("page={0}".format(context["page"]), "page={0}".format(context["page"]+1))
        context["page"] += 1
        session.do(Request(context["url"]), process_reviews, dict(context))

    elif product.reviews:
        session.emit(product)
