from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.makeuseof.com/category/product-reviews/', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h5[@class="display-card-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_page = data.xpath('//a[@class="next"]')
    if next_page:
        next_page = context.get('page', 1) + 1
        session.queue(Request('https://www.makeuseof.com/category/product-reviews/' + str(next_page) + '/', use='curl'), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(':')[0].replace('Review', '').replace('review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('').string()