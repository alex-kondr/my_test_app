from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.stuff.tv/reviews", use="curl"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//div[@id='filter-dropdown-product-category']/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, use="curl"), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    prods = data.xpath("//article[not(preceding::aside[@id='secondary'])]/following-sibling::div[1]//h2[@class='c-entry__title']/a")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url, use='curl'), process_review, dict(context, name=name, url=url))

    next_page = data.xpath("//div[@class='nav-previous']/a/@href").string()
    if next_page:
        session.queue(Request(next_page, use='curl'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context["name"].split(" review")[0].split(" Review")[0]
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = context["cat"]

    review = Review()
    review.type = "pro"
    review.title = context["name"]
    review.ssid = product.ssid
    review.date = data.xpath("//div[@class='c-singular__author']//time[contains(@class, 'published')]/@datetime").string().split('T')[0]
    review.url = product.url
    grade_overall = data.xpath("//div[contains(@class, 'c-singular__rating')]/@class").string()
    if grade_overall:
        grade_overall = int(grade_overall.split("is-rating-")[-1])
        review.grades.append(Grade(type="overall", value=grade_overall, best=5))

    author = data.xpath("//span[@class='c-singular__author-name-text']/a").first()
    if author:
        name = author.xpath("text()").string()
        url = author.xpath("@href").string()
        ssid = url.split('/')[-2]
        review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

    pros = data.xpath("//p[@class='c-stuff-says__good-stuff-item']/text()")
    for pro in pros:
        pro = pro.string()
        review.add_property(type="pros", value=pro)

    cons = data.xpath("//p[@class='c-stuff-says__bad-stuff-item']/text()")
    for con in cons:
        con = con.string()
        review.add_property(type="cons", value=con)

    summary = data.xpath("//div[@class='c-singular__text']//p[@class='c-stuff-says__verdict']/text()").string()
    if not summary:
        summary = data.xpath("//p[@class='c-singular__subtitle']/text()").string()
    if not summary:
        summary = data.xpath("(//div[@class='c-singular__text']//p/strong)[1]/text()").string()
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//div[@class='c-singular__text']//*[contains(local-name(), 'h')][contains(@id, 'verdict')]/following-sibling::p[not(@class)]/text()").string()
    if not conclusion:
        conclusion = data.xpath("//div[@class='c-singular__text']//*[contains(local-name(), 'h')][contains(text(), 'verdict')]/following-sibling::p[not(@class)]/text()").string()
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[@class='c-singular__text']//p[not(@class)][not(strong)][not(a)]//text()").string(multiple=True)
    if excerpt:
        excerpt = excerpt.split("Stuff says: ")[0]
        if conclusion:
            excerpt = excerpt.split(conclusion.strip())[0]
        if summary:
            excerpt = excerpt.replace(summary.strip(), '')
        excerpt = excerpt.strip()
        review.add_property(type="excerpt", value=excerpt)
        product.reviews.append(review)
        session.emit(product)
