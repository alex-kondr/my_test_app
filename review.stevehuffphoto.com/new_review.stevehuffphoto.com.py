from agent import *
from models.products import *


XCAT = ['IN USE', 'News']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.stevehuffphoto.com/all-reviews/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//span[@style="font-size: 14pt;"]//a')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//p[not(@style)]//a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(@href, "bhpho.to") and (contains(., "You can buy") or contains(., "you can see that offer"))]/@href').string()
    if not product.url:
        product.url = context['url']

    cats = data.xpath('(//span[@class="entry-meta-categories"])[1]/a/text()').strings()
    if cats:
        product.category = '|'.join([cat.strip() for cat in cats if cat.strip() not in XCAT])

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    review.authors.append(name='Steve Huff', ssid='Steve Huff')


