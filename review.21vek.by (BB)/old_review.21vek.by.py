#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


X_CATS = ['Уценка', 'Мебель', 'Сад и огород', 'Матрасы', 'Диваны', 'Двери']


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


def RequestRevs(url):
    options = "--compressed -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/112.0' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Accept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'X-Requested-With: XMLHttpRequest'"
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.21vek.by/'), process_frontpage, {})


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="styles_promoItems__2Tq3m"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        if name not in X_CATS:
            session.queue(Request(url), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats1 = data.xpath('//div[@class="b-page"]/p/a')
    for cat1 in cats1:
        name = cat1.xpath('img/@alt').string()
        url = cat1.xpath('@href').string()
        if name not in X_CATS:
            session.queue(Request(url), process_prodlist, dict())
        
    if not cats1:
        process_prodlist(data: Response, context: dict[str, str], session: Session)


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)
    
    prods = data.xpath('//li[contains(@class, "result__item")]/dl')
    for prod in prods:
        name = prod.xpath('.//span[@class="result__name"]//text()').string()
        url = prod.xpath('.//a[@class="mindbox-pr-view result__link j-ga_track"]/@href').string()
        sku = prod.xpath('.//a[@class="mindbox-pr-view result__link j-ga_track"]/@data-code').string()

        revs = prod.xpath('.//span[@class="b-reviews-rate-catalog result__tools-item"]')
        if revs and not session.seen(sku):
            session.queue(Request(url), process_product, dict(name=name, url=url, sku=sku))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict())


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url']
    pr['manufacturer'] = data.xpath('//meta[@itemprop="brand"]/@content').string()
    pr['category'] = data.xpath('//div[@class="l-buyzone"]//span[contains(@class, "g-item-data j-item-data")]/@data-category').string().replace(' / ', "|")

    if pr['manufacturer']:
        pr['category'] = pr['category'].replace(pr['manufacturer'], '').rstrip('|')

    pr['ssid'] = data.xpath('//meta[@itemprop="productID"]/@content').string()
    pr['sku'] = context['sku']

    context['product'] = pr
    process_reviews(data: Response, context: dict[str, str], session: Session)


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['product']['name']
    product.category = context['product']['category']
    product.url = context['product']['url']
    product.manufacturer = context['product']['manufacturer']
    product.ssid = context['product']['ssid']
    product.sku = context['product']['sku']


    revs = data.xpath('//ul[@class="b-reviews"]/li')
    if not revs:
        revs_json = simplejson.loads(data.content)
        new_data = data.parse_fragment(revs_json['content'])
        revs = new_data.xpath('//ul[@class="b-reviews"]/li')        

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('span[@class="reviews__date"]//text()').string()

        ssid = rev.xpath('@id').string()
        if ssid:
            review.ssid = ssid.split('-')[-1]

        author = rev.xpath('span[@itemprop="author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('span[@class="b-reviews-rate"]/span/@class').string()
        if grade_overall:
            grade_overall = grade_overall.split('-')[-1]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        
        pros = rev.xpath('span[@class="reviews__body"][span[contains(text(), "Плюсы:")]]/text()').string(multiple=True)
        if pros:
            review.add_property(type='pros', value=pros)
        
        cons = rev.xpath('span[@class="reviews__body"][span[contains(text(), "Минусы:")]]/text()').string(multiple=True)
        if cons:
            review.add_property(type='cons', value=cons)

        excerpt = rev.xpath('span[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
    
    revs_cnt = context.get('revs_cnt')
    if not revs_cnt:
        revs_cnt = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    offset = context.get('offset', 0) + 10

    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        rev_link = context.get('rev_link')
        if not rev_link:
            rev_link = data.xpath('//span[@class="j-paginator g-pseudo_href"]/@data-href').string()
        revs_url = "https://www.21vek.by" + rev_link + "?page={page}&hash=".format(page=next_page)
        session.queue(RequestRevs(revs_url), process_reviews, dict(context, rev_link=rev_link, offset=offset, page=next_page, revs_cnt=revs_cnt))
