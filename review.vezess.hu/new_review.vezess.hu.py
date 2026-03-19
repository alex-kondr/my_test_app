from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("https://www.vezess.hu/ujauto-teszt/"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[contains(@class, 'm-list__item')]")
    for rev in revs:
        title = rev.xpath(".//a[@class='m-list__titleLink']/@title").string()
        url = rev.xpath(".//a[@class='m-list__titleLink']/@href").string()
        ssid = rev.xpath("@post_id").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url, ssid=ssid))

    next_url = data.xpath("//a[@class='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    if not json:
        return

    product = Product()
    product.ssid = str(context["ssid"])
    product.url = context["url"]

    try:
        rev_json = simplejson.loads(data.xpath("//script[contains(., 'itemReviewed')]/text()").string())

        product.name = json["itemReviewed"]["name"].strip()
    

    if not name:
        name = data.xpath("//h1[contains(@class,'o-post__title')]/text()").string()
        if name:
            name = name.split('Teszt:')[-1].split('–')[0]
    if not name:
        name = data.xpath("//h1[@class='m-newCarTest__title']/text()").string()
    if not name:
        name = data.xpath('//title/text()').string()
        if name:
            name = name.split('Vezettük: ')[-1]
    product.name = name.strip()

    cat = json["itemReviewed"].get("category")
    product.category = "Cars|" + cat if cat else "Cars"

    manufacturer = json["itemReviewed"]["brand"]
    if manufacturer.get("name"):
        product.manufacturer = manufacturer["name"]

    review = Review()
    review.type = "pro"
    review.title = context["title"]
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[contains(@class, 'm-author__authorName')]").first()
    if author:
        name = author.xpath("@title").string()
        url = author.xpath("@href").string()
        review.authors.append(Person(name=name, ssid=name, profile_url=url))

    grade_overall = json.get('reviewRating')
    if grade_overall:
        value = grade_overall.get('ratingValue')
        max_value = grade_overall.get('bestRating')
        if value and max_value:
            review.grades.append(Grade(type='overall', value=float(value), best=float(max_value)))

    pros = data.xpath("//td[@class='pros']//li")
    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True)
        review.add_property(type="pros", value=pro)

    cons = data.xpath("//td[@class='cons']//li")
    for con in cons:
        con = con.xpath(".//text()").string(multiple=True)
        review.add_property(type="cons", value=con)

    summary = data.xpath("//p[contains(@class,'o-post__lead lead')]/text()").string(multiple=True)
    if summary:
        summary = summary.strip()
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath("//h2[@id='ertekeles']/following-sibling::div/p/text()").string(multiple=True)
    if conclusion:
        conclusion = conclusion.strip()
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[contains(@class,"article-body")]//p[not(contains(@id, "caption-attachment"))][not(.//img)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class,"article-body")]//div[@class="paragraph"][not(.//h2)][not(.//table)][not(.//img)]//text() | //div[@class="paragraph"]//p[not(contains(@id, "caption-attachment"))]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, "")
        if summary:
            excerpt = excerpt.replace(summary, "")
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)
            session.emit(product)
