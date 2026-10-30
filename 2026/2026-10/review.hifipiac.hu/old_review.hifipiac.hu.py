from agent import *
from models.products import *


XCAT = ["Címlap", "Hírek", "Apróhirdetések", "Fórum"]


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.hifipiac.hu/"), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath("(//ul[contains(@class, 'nav-stacked')])[2]/li")
    for cat in cats:
        cat_name = cat.xpath("a/text()").string()
        url = cat.xpath("a/@href").string()
        subcats = cat.xpath("ul/li/a")
        if not subcats:
            session.queue(Request(url), process_revlist, dict(cat=cat_name, prods_url=url))
        for subcat in subcats:
            name = cat_name + '|' + subcat.xpath("text()").string()
            url = subcat.xpath("@href").string()
            session.queue(Request(url), process_revlist, dict(cat=name, prods_url=url))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath("//h2[@class='article-title']/a")
    for prod in prods:
        name = prod.xpath("@title").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))

    if prods:
        start_value = context.get("start_value", 0) + 12
        url = context["prods_url"] + "?limit=12&start=" + str(start_value)
        session.queue(Request(url), process_revlist, dict(context, start_value=start_value))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-1].split('-')[0]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.ssid = product.ssid
    review.url = product.url

    review.date = data.xpath("//dd[@class='create']//time/@datetime").string()
    if review.date:
        review.date = review.date.split('T')[0]

    conclusion = data.xpath("//div[contains(@class, 'article-content-main')]/p[descendant::span[@itemscope='itemscope'][strong[regexp:test(text(), 'Ajánlás', 'i')]]]/following-sibling::p//span[@itemscope='itemscope'][not(br)]//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[contains(@class, 'article-content-main')]/p[descendant::span[@itemscope='itemscope']]//strong[regexp:test(text(), 'Ajánlás', 'i')]/following-sibling::text()").string()
    if conclusion:
        conclusion = conclusion.strip()
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[contains(@class, 'article-content-main')]/*[self::p or self::ol]//span[@itemscope='itemscope'][not(regexp:test(., 'tel:|honlap:', 'i'))]//text()").string(multiple=True)
    if excerpt:
        excerpt = excerpt.strip()
        if conclusion:
            excerpt = excerpt.split(conclusion)[0]
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)
        session.emit(product)