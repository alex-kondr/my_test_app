from agent import *
from models.products import *


XCAT = ["Címlap", "Hírek", "Apróhirdetések", "Fórum"]


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.hifipiac.hu/"), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[contains(@class, "nav level0")]/li')
    for cat in cats:
        name = cat.xpath("a/text()").string()

        if name not in XCAT:
            subcats = cat.xpath(".//ul/li/a")
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath("text()").string()
                    url = subcat.xpath("@href").string()
                    session.queue(Request(url), process_revlist, dict(cat=name+'|'+subcat_name, cat_url=url))
            else:
                url = cat.xpath("a/@href").string()
                session.queue(Request(url), process_revlist, dict(cat=name, cat_url=url))

def process_revlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath("//h2[@class='article-title']/a")
    for prod in prods:
        name = prod.xpath("@title").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))

    if prods:
        offset = context.get("offset", 0) + 12
        url = context["cat_url"] + "?limit=12&start=" + str(offset)
        session.queue(Request(url), process_revlist, dict(context, offset=offset))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context["name"].split(' - Szép test')[0].strip()
    product.url = context["url"]
    product.ssid = product.url.split('/')[-1].split('-')[0]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath("//dd[@class='create']//time/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    # no author

    grades = data.xpath('//div[contains(@class, "article-content")]/p//text()[regexp:test(., "^[^0-9/]+:?\s*\d{2}\/\d{1,2}$")]')
    for grade in grades:
        grade = grade.string(multiple=True)
        if grade:
            grade = re.search("^([^0-9/:]+):?\s*\d{2}\/(\d{1,2})$", grade)
            if grade:
                grade_name = grade.group(1).strip()
                grade_val = grade.group(2).strip()
                if grade_name and grade_val and float(grade_val) > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    conclusion = data.xpath('//strong[normalize-space(text())="Ajánlás"]/following-sibling::text()|//strong[normalize-space(text())="Ajánlás"]/following-sibling::p[not(regexp:test(., "tel:|honlap:", "i"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[contains(@class, 'article-content')]/*[self::p or self::ol]//span[@itemscope='itemscope'][not(regexp:test(., 'tel:|honlap:', 'i'))]//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = excerpt.strip()
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
