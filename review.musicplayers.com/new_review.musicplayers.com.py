from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://musicplayers.com/category/reviews/", force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='bk-blog-content clearfix']//h4/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url  = data.xpath('//link[@rel="next"]/@href').string()
    if next_url :
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace("Album Review:", "").replace("Album Review -", "").replace("ALBUM REVIEW:", "").replace("DVD Review:", "").split(":")[0].split(" - ")[0].strip()
    product.url = context['url']
    product.ssid = context['url'].split("/")[-2]

    categories = data.xpath("//div[@class='breadcrumbs']//span[@itemprop='title']/text()").strings()
    category = []
    if categories:
        for cat in categories[2:]:
            category.append(cat.replace('Reviews:', '').replace('Review:', '').replace('Reviews', '').replace('Review', '').strip())
    if category:
        product.category = '|'.join(category)

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = context['title']

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]').first()
    if author:
        name = author.xpath(".//text()").string()
        url = author.xpath("@href").string()
        ssid = url.split("/")[-2]
        review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

    grades = data.xpath("//tbody/tr/following-sibling::tr")
    for grade in grades:
        name = grade.xpath(".//strong/text()").string()
        if not name:
            name = grade.xpath(".//span/text()").string()

        value = grade.xpath(".//img/@src").string()

        if name and value and name != 'Overall Rating:':
            if len(value) > 1:
                value = value[0] + '.' + value[1:len(value) - 1]

            if len(grade.xpath(".//td")) == 3:
                value = grade.xpath(".//span/text()").string()

            value = value.split('/')[-1].split('.')[0].replace("finalstar-", "").replace("_stars", "").replace("_", "")
            try:
                if float(value) > 10.0:
                    value = float(value) / 10
                review.grades.append(Grade(name=name.replace(':', ''), value=float(value), best=4.0))
            except ValueError:
                pass

    grade_overall = data.xpath('//tr[contains(., "Overall Rating")]//text()|//span[contains(., "OVERALL RATING")]//text()|//tr[contains(., "Overall")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.lower().replace('overall', '').replace('rating', '').split('stars')[0].split('=')[-1].split(',')[0].strip()
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=4.0))

    excerpt = data.xpath("//div[@class='entrytext']/p/text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='article-content clearfix']/p/text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='article-content clearfix']/p/span/text()").string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    product.reviews.append(review)
    session.emit(product)
