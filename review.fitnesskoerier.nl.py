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
                

def process_category(data, context, session):
    prods = data.xpath('//div[@class="item is_grid with-sec-image"]')
    for prod in prods:
        name = prod.xpath('.//a[@class="m-img greyed"]/@title').string()
        url = prod.xpath('.//a[@class="m-img greyed"]/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))
        break#################################################################################################

    # page_numbers = data.xpath('//a[@class="s-pagination__link"]//text()').strings()
    # current_page_number = int(context['url'].split('/')[-1])
    # next_page_number = current_page_number + 1
    # if str(next_page_number) in page_numbers:
    #     next_url = context['url'].replace(str(current_page_number), str(next_page_number))
    #     session.queue(Request(next_url), process_category, dict(cat=context['cat'], url=next_url))