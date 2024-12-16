from agent import *
from models.products import *


XCAT = ['Clearance', 'Brands', 'Hot Deals']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.smarthomesounds.co.uk/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[regexp:test(@class, "^level-0")]')
    for cat in cats:
        name = cat.xpath('.//text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    cats = data.xpath('//a[@class="group hover:underline"]')
    for cat in cats:
        name = cat.xpath('img/@title').string()
        url = cat.xpath('@href').string()

        if 'view all' not in name.lower() and 'offers' not in name.lower() and 'deals' not in name.lowewr():
            session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + name))
