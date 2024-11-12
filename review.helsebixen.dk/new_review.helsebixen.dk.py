from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.helsebixen.dk/', use='curl'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[contains(@class, "navigation-offcanvas")]/li/a[not(@title="Brands")]')
    for cat in cats:
        name = cat.xpath('@title').string()
        url = cat.xpath('@data-href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))
