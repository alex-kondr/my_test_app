from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.the-ambient.com/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "grid-card")]//h2[@class="is-title post-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')

    product.category = data.xpath('//span[@class="meta-item cat-labels"]/a[@rel="category"]/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[span[@class="by"]]/a[@rel="author"]/text()').string()
    author_url = data.xpath('//span[span[@class="by"]]/a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count((//div[@class="full-stars"])[1]/i[@class="fa-solid fa-star"]) + count((//div[@class="full-stars"])[1]/i[@class="fa-solid fa-star-half"]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//div[@class="col" and .//h2[contains(., "Pros")]]/div/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="col" and .//h2[contains(., "Cons")]]/div/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//section[@class="review-summary"]/h2/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//section[@class="review-summary"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not(contains(., "Read our guide"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
