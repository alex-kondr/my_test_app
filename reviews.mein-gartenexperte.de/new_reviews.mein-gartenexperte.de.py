from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mein-gartenexperte.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "submenu index category")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul[@class="level_2"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/text()').string()

            sub_cats1 = sub_cat.xpath('ul[@class="level_3"]/li/a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string()
                    url = sub_cat1.xpath('@href').string()
                    session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    revs_json = data.xpath('//script[contains(., "window.products")]/text()').string()
    if revs_json:
        revs = simplejson.loads(revs_json.replace('="', '=\\"').replace('"\'', '\\""').replace('\'<', '"<').replace('" ', '\\" ').replace('">', '\\">').replace("'", '"').replace(',}', '}').replace(',]', ']'))
        for rev in revs:
            
