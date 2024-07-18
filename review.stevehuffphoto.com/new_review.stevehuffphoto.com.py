from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.stevehuffphoto.com/all-reviews/'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//span[@style="font-size: 14pt;"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        name = name if 'OLDER' not in name else 'Tech'
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//p[not(@style)]//a')
