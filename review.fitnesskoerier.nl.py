from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.fitnesskoerier.nl/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats1 = data.xpath('//li[@class="item sub use_mega"]')
    for cat1 in cats1:
        name1 = cat1.xpath('a//text()').string()
        
        cats2 = cat1.xpath('.//div[@class="col flex flex-column"]')        
        for cat2 in cats2:
            name2 = cat2.xpath('.//a[@class="title"]//text()').string()
        
            cats3 = cat2.xpath('.//a[@class="subtitle"]')
            for cat3 in cats3:
                name3 = cat3.xpath('text()').string()
                url = cat3.xpath('@href').string()
                session.queue(Request(url), process_category, dict(cat=name1+"|"+name2+"|"+name3, url=url))