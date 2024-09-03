from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.haus.de/test'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="css-1pip4vl"]')
    for cat in cats:
        name = cat.xpath('div[@class="css-60z25j"]/text()').string()

        sub_cats = cat.xpath('div/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name))
