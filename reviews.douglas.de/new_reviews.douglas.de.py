from agent import *
from models.products import *
import simplejson


XCAT = ['MARKEN', 'OSTERN', 'SALE', 'Nachhaltigkeit', 'LUXUS', 'NEU', 'Beauty-Storys', 'Douglas Beauty Tester', '']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.douglas.de/de', use='curl', force_charset='utf-8'), process_fronpage, dict())


def process_fronpage(data, context, session):
    cats = data.xpath('//li[@class="navigation-main-entry" and .//a[normalize-space()]]')
    for cat in cats:
        name = cat.xpath('.//a[contains(@class, "navigation-main-entry__link")]/text()').string()
        sub_cats_id = cat.xpath('@data-uid').string()

        if name not in XCAT:
            url = 'https://www.douglas.de/api/v2/navigation/nodes/{sub_cats_id}/children'.format(sub_cats_id=sub_cats_id)
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats_json = simplejson.loads(data.content)

    sub_cats = sub_cats_json.get('nodes', [])
    for sub_cat in sub_cats:
        sub_name = sub_cat.get('title')

        sub_cats1 = sub_cat.get('children', [])
        if sub_cats1 and sub_name not in XCAT:
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.get('title')
                url = 'https://www.douglas.de' + sub_cat1.get('entries', [{}])[0].get('component', {}).get('otherProperties', {}).get('url')

                if 'Alle' not in sub_name1:
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name + '|' + sub_name1))
                else:
                    url = 'https://www.douglas.de' + sub_cat.get('entries', [{}])[0].get('component', {}).get('otherProperties', {}).get('url')
                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))

        elif sub_name not in XCAT:
            url = 'https://www.douglas.de' + sub_cat.get('entries', [{}])[0].get('component', {}).get('otherProperties', {}).get('url')
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-grid-column")]')
    for prod in prods:
        name = prod.xpath('.//div[@class="text brand-line" or @class="text name"]//text()').string(multiple=True)
        manufacturer = prod.xpath('.//div[@class="text top-brand"]/text()').string()
        url = prod.xpath('.//a[@linkappearance="true"]/@href').string().split('?')[0]

        revs_cnt = prod.xpath('.//span[@data-testid="ratings-info"]')
        if revs_cnt:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))