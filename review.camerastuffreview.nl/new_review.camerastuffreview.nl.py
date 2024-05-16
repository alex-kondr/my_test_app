from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://camerastuffreview.com/lenzen/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="elementor-post__title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="page-numbers next"]/@href')
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '')
