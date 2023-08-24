from agent import *
from models.products import *


def run(context, session): 
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.eurogamer.nl/archive/reviews'), process_frontpage, dict())


def process_frontpage(data, context, session):
    for p in data.xpath("//ul[@class='summary_list']/li/a"):
        title = p.xpath("@title").string()
        url = p.xpath("@href").string()
        if title and url:
            session.queue(Request(url), process_review, dict(context, url=url, title=title))

    next_url = data.xpath("//div[@class='next']/a[1][@class='button pagination_button']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_frontpage, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review')[0]
    product.url = context['url']
    product.category = "Games"
    product.ssid = product.url.split('/')[-1]

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    review.date = data.xpath("//div[@class='published_at']/time/@datetime").string()
    if review.date:
        review.date = review.date.split(' ')[0]
    if not review.date:
        review.date = data.xpath("//div[@class='updated_at']/time/@datetime").string()
        if review.date:
            review.date = review.date.split(' ')[0]

    author_name = data.xpath("//div[@class='author']//a//text()").string()
    author_url = data.xpath("//div[@class='author']//a/@href").string()
    if author_url and author_name:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, url=author_url, ssid=author_ssid))

    grade_overall = data.xpath("//span[@class='review_rating_value']//text()").string()
    grade_best = data.xpath("//span[@class='review_rating_max_value']//text()").string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=float(grade_best)))

    summary = data.xpath('//span[@class="strapline"]//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion_section = data.xpath('//div[@class="article_body"]//section[@class="synopsis"]')
    if conclusion_section:
        conclusion_content = data.xpath("//div[@class='article_body_content']//text()")
        for conclusion in conclusion_content:
            conclusion = conclusion.string()
            if conclusion != '':
                review.add_property(type="conclusion", value=conclusion)
                break
    else:
        conclusion = data.xpath('//div[@class="article_body"]//section[@class="conclusion"]//following::p[1]//text()').string(multiple=True)
        if conclusion:
            review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="article_body"]//p//text()').string(multiple=True)

    next_url = data.xpath('//div[@class="next"][1]/a/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, excerpt=excerpt, review=review))
    else:
        if excerpt:
            if conclusion:
                excerpt = excerpt.replace(conclusion, '')
            review.add_property(type='excerpt', value=excerpt)

    product.reviews.append(review)
    session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    excerpt = context['excerpt']
    excerpt += ' ' + data.xpath('//div[@class="article_body"]//p//text()').string(multiple=True)

    url = data.xpath('//link[@rel="canonical"]/@href').string()
    review.add_property(type='pages', value=dict(title=review.title, url=url))

    next_url = data.xpath('//div[@class="next"][1]/a/@href').string()   
    if next_url:   
        session.do(Request(next_url), process_review_next, dict(context, review=review))
    else:
        review.add_property(type="excerpt", value=excerpt)

    grade_overall = data.xpath("//span[@class='review_rating_value']//text()").string()
    grade_best = data.xpath("//span[@class='review_rating_max_value']//text()").string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=float(grade_best)))
