from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("http://bgr.com/reviews/"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//article/following::a[img][1]")
    for rev in revs:
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath("//link[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    title = data.xpath("//h1[@class='entry-title']//text()").string()

    product = Product()
    product.name = title.split(" Review")[0].split(" review")[0]
    product.url = context["url"]
    product.ssid = context["url"].split('/')[-2]
    product.category = data.xpath("(//div[contains(@class,'bgr-breadcrumbs')]//a)[last()]//text()").string()

    review = Review()
    review.url = context["url"]
    review.title = title
    review.date = data.xpath("//meta[@property='article:published_time']/@content").string().split('T')[0]
    review.ssid = product.ssid
    review.type = "pro"

    author = data.xpath("//a[@rel='author']").first()
    if author:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    grade_overall = len(data.xpath("//span[@class='bgr-rating bgr-clip-100 bgr-rating-solid']"))
    if grade_overall > 0:
        grade_overall += len(data.xpath("//span[@class='bgr-rating bgr-clip-50 bgr-rating-solid']")) / 2
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

    conclusion = data.xpath("//h2[regexp:test(normalize-space(.), 'conclusions|verdict', 'i')]/following-sibling::p[1]//text()").string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath("//div[contains(@class,'entry-content')]//p//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)
        session.emit(product)
