from agent import *
from models.products import *
import unicodedata 


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.softonic.com.br'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[label[contains(@class, "menu-toggle-button")] and .//strong[contains(text(), "Home")]]')
    for cat in cats:
        name = cat.xpath(".//strong//text()").string().replace('Home', '').strip()
        print()
        print('name=', name)

        subcats = cat.xpath(".//li[not(.//div)]/a")
        for subcat in subcats:
            subcat_name = subcat.xpath("text()").string()
            print('subcat_name=', unicodedata.normalize('NFD', subcat_name).decode('ascii', 'ignore'))
            url = subcat.xpath("@href").string()
            # session.queue(Request(url), process_category, dict(cat=name+"|"+subcat_name))


# def process_category(data, context, session):
#     prods = data.xpath("//div[@class='product__details__title product__details__title--branded']/a")
#     for prod in prods:
#         name = prod.xpath("@title").string()
#         url = prod.xpath("@href").string()
#         session.queue(Request(url), process_product, dict(context, url=url, name=name))

#     next_url = data.xpath('//link[@rel="next"]/@href').string()
#     if next_url:
#         session.queue(Request(next_url), process_category, dict(context))