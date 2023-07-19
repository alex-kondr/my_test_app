from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://musicplayers.com/category/reviews/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    revs = data.xpath("//ul[@class='bk-blog-content clearfix']//h4/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_page = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_page:
        session.queue(Request(next_page), process_frontpage, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace("Album Review: ", "")
    product.url = context['url']
    product.ssid = context['url'].split("/")[-2]
    product.category = data.xpath("//div[@class='breadcrumbs']//span[@itemprop='title']/text()")[2:].join('|')

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = context['title']
    review.date = data.xpath("//div[@class='s-post-header container']//div[@class='post-date']/text()").string()

    author = data.xpath("//div[@class='s-post-header container']//div[@class='post-author']/a").first()
    if author:
        name = author.xpath(".//text()").string()
        url = author.xpath("@href").string()
        ssid = url.split("/")[-2]
        review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

    grades = data.xpath("//tbody/tr[1]/following-sibling::tr")
    for grade in grades:
        name = grade.xpath(".//strong/text()").string()
        if not name:
            name = grade.xpath(".//span[1]/text()").string()

        value = grade.xpath(".//img/@src").string()

        if name and value and name != 'Overall Rating:':
            if len(value) > 1:
                value = value[0] + '.' + value[1:len(value) - 1]

            if len(grade.xpath(".//td")) == 3:
                value2 = grade.xpath(".//span[1]/text()").string()

            value = value.split('/')[-1].split('.')[0].replace("finalstar-", "").replace("_stars", "").replace("_", "")
            try:
                if float(value) > 10.0:
                    value = float(value) / 10
                review.grades.append(
                    Grade(name=name.replace(':', ''), value=float(value), best=4.0))
            except ValueError:
                pass

    grade_overall = data.xpath("//tbody/tr[last()]/td[2]/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//tbody/tr[last()]/td[1]//b/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//tbody/tr[last()]/td[2]/em/text()[2]").string()
    if not grade_overall:
        grade_overall = data.xpath("//tbody[1]/tr[last()]//span/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//tbody/tr[last()]/td[2]/em/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//tbody[1]/tr[last()]//b[1]/text()[2]").string(multiple=True)
        if grade_overall:
            grade_overall = grade_overall.split(" =")[1].split(" Stars")[0]

    if grade_overall:
        grade_overall = grade_overall.replace("OVERALL RATING = ", "").replace(" Stars, which earns it a", "").replace("OVERALL RATING = ", "").replace(" Stars", "").replace(" (out of 4)", "").replace(",", "").replace(" WIHO Award!", "")
        try:
            review.grades.append(
                Grade(type='overall', value=float(grade_overall), best=4.0))
        except ValueError:
            pass

    excerpt = data.xpath("//div[@class='entrytext']/p/text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='article-content clearfix']/p/text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='article-content clearfix']/p/span/text()").string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    product.reviews.append(review)
    session.emit(product)
