from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.giga.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@class='alice-navbar-topnav nav navbar-nav']/li/a")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath(".//text()").string(multiple=True)
        session.queue(Request(url), process_category, dict(context, url=url, cat=name))


def process_category(data, context, session):
    cats = data.xpath("//ul[@class='nav navbar-nav']/li[contains(.,'Test')]/a")
    for cat in cats:
        url = cat.xpath("@href").string()
        session.queue(Request(url), process_revlist, dict(context, url=url))


def process_revlist(data, context, session):
    revs = data.xpath("//h2[@class='alice-teaser-title']/a[@class='alice-teaser-link']")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))
    
    nexturl = data.xpath("//li[@class='pagination-next']/a/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' im Test')[0]
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']
    product.url = context['url']
    
    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//div[@class='page-header-meta']/time[@class='article-published-date']/@datetime").string().split('T')[0]
    
    authors = data.xpath("//div[@class='page-header-meta']/a[@class='page-author']")
    for author in authors:
        author_name = author.xpath(".//text()").string(multiple=True)
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    conclusion = data.xpath("//div[@class='product-rating']/blockquote//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    
    excerpt = data.xpath("//div[@class='article-body']/p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//body/p//text()").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    grade_overall = data.xpath("//div[@class='product-rating-rating']/strong//text()").string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
    
    product.reviews.append(review)
    session.emit(product)
