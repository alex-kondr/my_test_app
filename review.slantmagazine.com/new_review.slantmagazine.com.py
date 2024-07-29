from agent import *
from models.products import *


XCAT = ['Home', 'News', 'Giveaways', 'About', 'Donate']


def run(contex, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.slantmagazine.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="menu-fly-out-menu"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3[@itemprop="headline"]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    title = data.xpath('//title//text()').string(multiple=True)

    product = Product()
    product.name = title.replace('Final Preview', '').replace('Previewing', '').replace('Previews', '').replace(' Preview -', '').replace('Preview: ', '').replace('Review:', '').replace('REview: ', '').replace(' Review', '').split('...')[0].strip()
    product.ssid = context['url'].split('/')[-2].replace('review-', '').replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[@rel="sponsored"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//i[@class="fa fa-star"])')
    grade_overall_half = data.xpath('count(//i[@class="fa fa-star-half-o"])')
    grade_best = data.xpath('count(//i[contains(@class, "fa fa-star")])')
    if grade_overall and grade_overall > 0:
        grade_overall += grade_overall_half / 2 if grade_overall_half else 0
        review.grades.append(Grade(type='overall', value=grade_overall, best=grade_best))

    summary = data.xpath('//div[contains(@class, "post-item-subtitle")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Overall")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Overall")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="content-main"]/div/p//text()').string(multiple=True)

    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
