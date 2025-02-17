from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.popsci.com/category/gear/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[contains(@class, "tag-list-item")]/a')
    if cats:
        for cat in cats:
            context['cat'] = context.get('cat', '') + '|' + cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url), process_catlist, dict(context))
    else:
        context['cat'] = context['cat'].strip('|')

        process_revlist(data, context, session)


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "post-content")]')
    for rev in revs:
        title = rev.xpath('.//span[contains(@class, "desktop")]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@name="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[contains(@class, "item-author")]//a').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('pros')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('cons')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('summ').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('sonlu').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('...').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('...').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
