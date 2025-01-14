from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = "True"
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.amateurphotographer.co.uk/reviews"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='posts-list']/li")
    for rev in revs:
        name = rev.xpath(".//h3/a/text()").string()
        url = rev.xpath(".//h3/a/@href").string()
        ssid = rev.xpath("@class").string()[5:12].replace(" r", '')
        grade = rev.xpath(".//img[@class='stars']/@src").string()
        if grade:
            grade = float(grade.split("rating-")[1].replace(".png", '')) / 20
        session.queue(Request(url), process_review, dict(name=name, url=url, ssid=ssid, grade=grade))

    next_page = data.xpath("//a[@class='icon next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath("//h3[@class='productname']/text()").string() or context["name"].split('|')[0].split(" review")[0].split(" Test")[0].strip()
    product.ssid = context["ssid"]
    product.url = context["url"]
    product.category = context["url"].split('/')[-2]
    product.manufacturer = data.xpath("//div[contains(@class,'manufacturer')]/a/text()").string()

    review = Review()
    review.type = "pro"
    review.ssid = product.ssid
    review.title = context["name"]
    review.url = context["url"]
    review.date = data.xpath("//h4/text()").string()

    if context["grade"]:
        review.grades.append(Grade(type="overall", value=context["grade"], best=5.0))

    grades = data.xpath("//ul[@class='additionalratings']/li")
    for grade in grades:
        name = grade.xpath("strong/text()").string().split(':')[0]
        value = grade.xpath("img/@src").string()
        if value:
            value = value.split('/')[-1].split('-')[-1].split('.')[0].strip()
            if value and value.isdigit():
                value = float(int(value) / 20)
                review.grades.append(Grade(name=name, value=float(value), best=5.0))
        else:
            value = grade.xpath("text()").string(multiple=True)
            if value:
                value = value.split('/')[0].strip()
                if value and value.isdigit():
                    max_value = float(grade.xpath("text()").string(multiple=True).split('/')[1].strip())
                    review.grades.append(Grade(name=name, value=float(value), best=max_value))

    pros = data.xpath("//h3[contains(.,'Pros')]/following-sibling::ul/li/text()").strings()
    for pro in pros:
        pro = pro.replace("+ ", '').replace("- ", '').strip()
        if pro:
            review.add_property(type="pros", value=pro)

    cons = data.xpath("//h3[contains(.,'Cons')]/following-sibling::ul/li/text()").strings()
    for con in cons:
        con = con.replace("+ ", '').replace("- ", '').strip()
        if con:
            review.add_property(type="cons", value=con)

    excerpt = data.xpath("//div[@itemprop='reviewBody']/*[self::p or self::div]//text()").string(multiple=True)
    next_page = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    if next_page:
        if excerpt:
            review.add_property(type="summary", value=excerpt)
        session.do(Request(next_page), process_lastpage, dict(product=product, review=review, url=next_page))
        return

    summary = data.xpath("//div[@class='highlightbox']/h3/text()").string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//h2[regexp:test(., 'verdict|conclusion', 'i')]/following-sibling::p/text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion.strip(), '').strip()
        review.add_property(type="excerpt", value=excerpt)
        product.reviews.append(review)
        session.emit(product)


def process_lastpage(data, context, session):
    product = context["product"]
    review = context["review"]

    page = context.get("page", 1) + 1
    review.add_property(type="pages", value=dict(title=review.title+'-'+str(page), url=context["url"]))

    next_page = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    if next_page:
        session.do(Request(next_page), process_lastpage, dict(context, page=page, url=next_page))
        return

    conclusion = data.xpath("//div[@itemprop='reviewBody']/p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    product.reviews.append(review)
    session.emit(product)
