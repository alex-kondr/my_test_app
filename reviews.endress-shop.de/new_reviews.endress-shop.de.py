from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.endress-shop.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('')


def process_prodlist(data, context, session):
    next_url = data.xpath('//a[@aria-label="Nächste Seite"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))
