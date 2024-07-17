from agent import *
from models.products import *


def run(context, session):
   session.queue(Request('http://www.tabletsmagazine.nl/category/tablet-reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="card__body"]')
    for rev in revs:
        cats = rev.xpath('.//a[@class="card__category" and not(contains(., "Reviews"))]/text()').strings()
        title = rev.xpath('h4[@class="card__title"]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(cats=cats, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Review: ')[-1].split(' - ')[0].split(' – ')[0].split('reviews van de')[-1].replace('App-review:', '').replace('App review:', '').replace('Review + Vlog:', '').replace('Consumentenbond bekijkt', '').replace('(Deel 2, uitgebreide review)', '').replace('Preview & unboxing', '').replace('review op dag van lancering', '').replace('Eerste reviews', '').replace('Preview video: ', '').replace('Video: ', '').replace('(update)', '').replace('(video)', '').replace('review: ', '').replace('Review ', '').replace('Hands-on review', '').replace('hands-on review', '').replace(' reviews;', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Technik'

    ssid = data.xpath('//div/@data-product_id').string()
    if ssid and ssid.isdigit():
        product.ssid = ssid

    if context['cats']:
        cats = context['cats']
        product.category = '|'.join([cat.strip() for cat in cats])

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="post-author__content"]/a/text()').string()
    author_url = data.xpath('//div[@class="post-author__content"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author_url.split('/')[-2], profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="section--module--review__score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[contains(@class, "pros") and not(contains(@class, "section"))]//li')
    for pro in pros:
        pro = pro.xpath('text()').string()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "cons") and not(contains(@class, "section"))]//li')
    for con in cons:
        con = con.xpath('text()').string()
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="intro__preview"]//p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "Conclusie") or contains(., "conclusie")]|//h3[contains(., "Conclusie") or contains(., "conclusie")])/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="section__body"]/p//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
