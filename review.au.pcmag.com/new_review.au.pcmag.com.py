from agent import *
from models.products import *


XCAT = ['Reviews', 'reviews', 'Review', 'First Looks', 'Editors’ Choice']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://au.pcmag.com/reviews", use="curl", force_charset="utf-8", max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    revs = data.xpath("//ul[@class='blogroll']//li")
    for rev in revs:
        title = rev.xpath("div[@class='articlecontainer']//a/text()").string()
        url = rev.xpath("div[@class='articlecontainer']//a/@href").string()

        if url:
            session.queue(Request(url, use="curl", force_charset="utf-8", max_age=0), process_reviews, dict(title=title, url=url))

    page = data.xpath("//section[contains(@class,'broll')]/@data-pagenum").string()
    page_cnt = data.xpath("//section[contains(@class,'broll')]/@data-total").string()
    if int(page) < int(page_cnt):
        url = "https://au.pcmag.com/reviews?page="+ str(int(page)+1)
        session.queue(Request(url, use="curl", force_charset="utf-8", max_age=0), process_frontpage, dict())


def process_reviews(data, context, session):
    product = Product()
    product.name = context['title'].split("Review")[0].replace("'", "’")
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    category = data.xpath("//div[@class='breadcrumbs']//a[last()]//text()").string()
    if category and category not in XCAT:
        product.category = category.replace("'", "’")

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace("'", "’")
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//div[@class='article-info']//time/@datetime").string()
    if date:
        review.date = date.split("T")[0]

    author_name = data.xpath("//span[contains(@class,'hcard')]//a//text()").string()
    if not author_name:
        author_name = data.xpath("//span[contains(@class,'hcard')]//text()").string()

    author_url = data.xpath("//span[contains(@class,'hcard')]//a/@href").string()
    if author_name and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name.replace("'", "’"), ssid=author_ssid, profile_url=author_url))
    elif author_name:
        review.authors.append(Person(name=author_name.replace("'", "’"), ssid=author_name.replace("'", "’")))

    pros = data.xpath("//li[@class='pros']//ul[@class='pros-cons-list']//li")
    for pro in pros:
        pro = pro.xpath("text()").string().replace("'", "’")
        review.add_property(type='pros', value=pro)

    cons = data.xpath("//li[@class='cons']//ul[@class='pros-cons-list']//li")
    for con in cons:
        con = con.xpath("text()").string().replace("'", "’")
        review.add_property(type='cons', value=con)

    grade_overall = data.xpath("//div[@class='review_bottomline']//div[contains(@class,'editor_rating')]//b//text()").string()
    if grade_overall:
        grade_overall = float(grade_overall.split(" ")[0])
        if grade_overall >= 10:
            grade_overall = grade_overall / 10

        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    summary = data.xpath("//h2[@id='id_deck']//text()").string(multiple=True)
    if summary:
        summary = summary.replace("'", "’").strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath("//h2[contains(.,'Conclusion') or contains(.,'conclusions') or contains(.,'verdict') or contains(.,'Verdict')]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='summarygrey']//div[contains(@id,'__bottomline')]//text()").string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace("'", "’").strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@id='id_text']//p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@id='id_text']//text()").string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')

        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = excerpt.replace("'", "’").strip()
        if len(excerpt) > 3:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
