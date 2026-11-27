#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = [u'Paketlösningar', 'Nyheter', 'Kampanjer']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    r = agent.Request(url, force_charset='utf-8')
    return r


def RequestRevs(ssid, offset):
    url = 'https://api.gamifiera.com/v3/comments/search?product_id%3Agroup={ssid}&order=best&type=product_review&link=product_review&skip={offset}&take=5'.format(ssid=ssid, offset=offset)
    options = "-H 'x-gmf-merchant-id: 1200' -H 'x-gmf-language: sv'"
    r = agent.Request(url, force_charset='utf-8', use='curl', options='-s -L --insecure '+options)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.brl.se'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    cats = data.xpath('//li[contains(@class, "Kateg") and not(contains(@class, "topKateg")) and not(contains(@class, "undrKateg"))]')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        if name and name not in XCAT:
            cats1 = cat.xpath('.//li[contains(@class, "undrKateg")]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string(multiple=True)
                url = cat1.xpath('a/@href').string()

                subcats = cat1.xpath('ul/li/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string()

                        if subcat_name and url:
                            session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))

                elif cat1_name and url:
                    session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "gutter-md-B gutter-md-T")]/div')
    for prod in prods:
        name = prod.xpath('.//div[@class="PT_Faktaruta"]/a//text()').string(multiple=True)
        url = prod.xpath('.//div[@class="PT_Faktaruta"]/a/@href').string()

        if name and url and not session.seen(url):
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath(u'//a[contains(., "Nästa")]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    try:
        prod_json = data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string()
        prod_json = simplejson.loads(prod_json)
    except:
        return

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['category'] = context['cat']
    pr['manufacturer'] = prod_json.get('brand', {}).get('name')
    pr['mpn'] = prod_json.get('sku')
    pr['ean'] = prod_json.get('gtin8')

    if pr['mpn'] and not session.seen(pr['mpn']):
        session.queue(RequestRevs(pr['mpn'], 0), process_reviews, dict(product=pr))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = context['product']['category']
    product.add_property(type='id.manufacturer', value=context['product']['mpn'])

    manufacturer = context['product'].get('manufacturer')
    if manufacturer and len(manufacturer.strip()) > 1:
        product.manufacturer = manufacturer.strip()

    ean = context['product'].get('ean')
    if ean and str(ean).isdigit() and len(str(ean)) > 10:
        product.add_property(type='id.ean', value=str(ean))

    try:
        revs_json = simplejson.loads(data.content)
    except:
        revs_json = {}

    revs = revs_json.get('comments', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('author', {}).get('firstName', '') + ' ' + rev.get('author', {}).get('lastName', '')
        author_ssid = rev.get('author', {}).get('id')
        if author and author.strip() and author_ssid:
            author = author.strip()
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author and author.strip():
            author = author.strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('content', {}).get('ratings', {}).get('product_score', {}).get('value')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.get('isVerified')
        if is_verified_buyer is True:
            review.add_property(type='is_verified_buyer', value=True)

        votes = rev.get('votes') or {}
        hlp_yes = votes.get('upvotes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = votes.get('downvotes')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        pros = rev.get('content', {}).get('pros', [])
        for pro in pros:
            pro = pro.strip(u' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

        cons = rev.get('content', {}).get('cons', [])
        for con in cons:
            con = con.strip(u' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

        title = rev.get('content', {}).get('title')
        excerpt = rev.get('content', {}).get('text')
        if excerpt and len(excerpt.strip()) > 2:
            if title:
                review.title = title.strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    revs_cnt = context.get('revs_cnt', revs_json.get('totalCount', 0))
    offset = context.get('offset', 0) + 5
    if revs_cnt and offset < int(revs_cnt):
        session.queue(RequestRevs(context['product']['mpn'], offset), process_reviews, dict(context, offset=offset, revs_cnt=int(revs_cnt)))
