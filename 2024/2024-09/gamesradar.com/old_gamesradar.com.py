from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://www.gamesradar.com/all-platforms/reviews/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//div[@id='review-tabs']/ul/li/span/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url), process_subcatlist, dict(cat=name))


def process_subcatlist(data, context, session):
    subcats = data.xpath("//ul[@class='list-grid contains-optional-content']/li/span/a")
    for subcat in subcats:
        name = subcat.xpath("text()").string()
        url = subcat.xpath("@href").string()
        session.queue(Request(url), process_revlist, dict(cat=context["cat"]+'|'+name))

    if not subcats:
        process_revlist(data, context, session)


def process_revlist(data, context, session):
    revs = data.xpath("//h3[@class='article-name']/span/text()")
    for rev in revs:
        name = rev.string()
        url = rev.xpath("preceding::a[@class='article-link'][1]/@href").string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context["url"]
    product.ssid = context["url"].split('/')[-2]
    product.category = context["cat"].replace('Game Reviews', 'Games')

    name = data.xpath('//div[@class="verdict-product"]//text()').string() or context["name"]
    product.name = name.split(" Review")[0].split(" review")[0].split("REVIEW")[0].strip()

    review = Review()
    review.type = "pro"
    review.title = context["name"]
    review.url = context["url"]
    review.ssid = product.ssid
    review.date = data.xpath("//time/@datetime").string().split('T')[0]

    authors = data.xpath("//a[@rel='author']")
    for author in authors:
        name = author.xpath(".//text()").string(multiple=True)
        url = author.xpath("@href").string()
        ssid = url.split('/')[-2]
        review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

    grade_overall = data.xpath("//div[@class='out-of-score-text']/p//text()").string()
    if grade_overall:
        grade_overall = grade_overall.split(" out of ")
        review.grades.append(Grade(type="overall", value=float(grade_overall[0]), best=float(grade_overall[1])))

    pros = data.xpath("//div[contains(@class, 'pro-con')]//h4[contains(., 'Pros')]/following-sibling::ul[1]/li/span/text()").strings()
    for pro in pros:
        pro = pro.replace('+', '').strip()
        if pro:
            review.add_property(type="pros", value=pro)

    cons = data.xpath("//div[contains(@class, 'pro-con')]//h4[contains(., 'Cons')]/following-sibling::ul[1]/li/span/text()").strings()
    for con in cons:
        con = con.replace('-', '').strip()
        if con:
            review.add_property(type="cons", value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2/text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//p[contains(@class,'verdict')]//text()").string()
    if not conclusion:
        conclusion = data.xpath("//div[contains(@class, ' verdict')]//p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//*[regexp:test(local-name(), 'h\d')][regexp:test(., 'overall', 'i')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[@id='article-body']/p//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary.strip(), '')
        if conclusion:
            excerpt = excerpt.replace(conclusion.strip(), '')
        excerpt = excerpt.strip()
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)
            product.reviews.append(review)
            session.emit(product)
