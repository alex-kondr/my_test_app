from agent import *
from models.products import *

import simplejson


def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://id.nl/'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="flex flex-row justify-start w-full"]/a')
    sub_cats = data.xpath('//div[@class="hidden navigation_navigation-sub-menu__V_oxX"]')
    for cat, sub_cat in zip(cats, sub_cats):
        name = cat.xpath('.//span/text()').string()

        sub_cats_ = sub_cat.xpath('.//div[contains(@class, "flex-1")]')
        for sub_cat in sub_cats_:
            sub_name = sub_cat.xpath('.//span/text()').string()
            sub_url = sub_cat.xpath('div/a/@href').string()

            sub_cats2 = sub_cat.xpath('.//li')
            for sub_cat2 in sub_cats2:
                sub_name2 = sub_cat2.xpath('.//div/text()').string()
                url = sub_cat2.xpath('a/@href').string()
                if sub_name2:
                    session.queue(Request(url + '?filter=Reviews&catid=47700387'), process_revlist, dict(cat=name + '|' + sub_name + '|' + sub_name2, url=url))
                    return

            session.queue(Request(sub_url + '?filter=Reviews&catid=47700387'), process_revlist, dict(cat=name + '|' + sub_name, url=sub_url))


def process_revlist(data, context, session):
    offset = context.get('offset')
    product_groups = set()
    if offset:
        print('data=', data.raw)
        revs_json = simplejson.loads(data.raw)
        revs = revs_json.get('pages', {})
        total_pages = revs_json.get('totalPages', {}).get('count', 21)
        print('total_pages=', total_pages)
    else:
        revs_json = data.xpath('//script[@type="application/json"]/text()').string()
        revs_json = simplejson.loads(revs_json)
        revs = revs_json.get('props', {}).get('pageProps', {}).get('pageData', {}).get('pages', {})

    print('count_revs', len(revs))
    for rev in revs:
        product_group_id = rev.get('productGroup', {}).get('id')
        if product_group_id:
            product_groups.add(product_group_id)

        ssid = rev.get('id')
        author = rev.get('author', {}).get('authorName')
        date = rev.get('publishedAt')
        title = rev.get('title')
        print('title=', title)
        url = context['url'] + '/' + rev.get('slug')
        session.queue(Request(url), process_review, dict(ssid=ssid, author=author, data=date, title=title, url=url))
        break

    product_group_ = ''
    for product_group in product_groups:
        product_group_ += '"' + str(product_group) + '",'

    if offset and offset + 100 < total_pages:
        offset = context['offset'] + 100
    elif not offset:
        offset = 20
    else:
        return
    options = """--compressed -X POST -H 'Content-Type: text/plain;charset=UTF-8' --data-raw '{"first":100,"skip":""" + str(offset) + ""","filter":{"pageType":{"eq":"47700387"}, "OR":{"productGroup":{"in":[""" + product_group_[:-1] + """]}}}}'"""
    print('options=', options)
    session.queue(Request('https://id.nl/api/content/pages', use='curl', options=options), process_revlist, dict(context, offset=offset))


def process_review(data,context, session):
    pass
