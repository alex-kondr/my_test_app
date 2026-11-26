#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = [u'Serviços', u'Carnê Digital']


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        line = line.replace('<!-- -->', '')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def Request(url):
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'TE: trailers'"
    r = agent.Request(url, use='curl', force_charset='utf-8', proxies=['rotating-eu'], options='-s -L --insecure '+options, max_age=0)
    return r


def RequestRevs(pid, page):
    url = "https://pdp-api.casasbahia.com.br/api/v2/reviews/product/" + pid + "/source/CB?page=" + str(page) + "&size=3"
    options = "-H 'accept: */*' -H 'accept-language: en-US;q=0.8,en;q=0.7' -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'"
    r = agent.Request(url, use='curl', force_charset='utf-8', proxies=['rotating-eu'], options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.casasbahia.com.br/'), process_frontpage, dict(context))


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[@class="horizontal-menu-navigation css-1cc34nb"]/a')
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('text()').string()
        if name not in XCAT:
            session.queue(Request(url), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[@class="styles__CategoryHeader-sc-c3e16b4e-1 kZgSoK"]/a')
    for subcat in subcats:
        url = subcat.xpath('@href').string()
        subcat_name = subcat.xpath('h3//text()').string()
        session.queue(Request(url), process_prodlist, dict(url=url, cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="product-card__details-wrapper"]')
    cnt = 0
    for prod in prods:
        cnt += 1
        url = prod.xpath('.//h3[@class="product-card__title"]/a/@href').string()
        name = prod.xpath('.//h3[@class="product-card__title"]/a//text()').string()
        revs_cnt = prod.xpath('.//span[@class="product-card__reviews-count-text"]//text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            revs_cnt = int(revs_cnt.strip('()'))
            session.queue(Request(url), process_product, dict(context, url=url, name=name, revs_cnt=revs_cnt))

    if prods and cnt >= 7:
        next_page = context.get('page', 1) + 1
        next_url = context['url'] + "&page=" + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['category'] = context['cat']
    pr['url'] = context['url']

    ean = data.xpath('''//script[contains(., '"ean":"')]//text()''').string()
    if ean:
        pr['ean'] = ean.split('"ean":"')[-1].split('"')[0]

    ssid = data.xpath('''//script[contains(., '"product":{"id":')]//text()''').string()
    if ssid:
        pr['ssid'] = ssid.split('"product":{"id":')[-1].split(',')[0]

    if pr.get('ssid') and not session.seen(pr['ssid']):
        session.queue(RequestRevs(pr['ssid'], 0), process_reviews, dict(product=pr, revs_cnt=context['revs_cnt']))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']

    ean = context['product'].get('ean')
    if ean and ean.isdigit() == True and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)


    try:
        revs_json = simplejson.loads(data.content)
    except:
        return

    revs = revs_json.get('review', {}).get('userReviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev['id'])
        review.date = rev.get('date')

        author = rev.get('name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.get('likes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('dislikes')
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.get('text')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 3
    if context['revs_cnt'] > offset:
        next_page = context.get('page', 0) + 1
        session.queue(RequestRevs(product.ssid, next_page), process_reviews, dict(context, offset=offset, page=next_page))
