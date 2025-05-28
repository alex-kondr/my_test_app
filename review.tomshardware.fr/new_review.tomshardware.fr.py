from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.tomshardware.fr/category/test/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Mini test :', '').replace('Test :', '').split(' : ')[0].split(' en test')[0].split(' et test')[0].replace('Test ', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('test-', '')
    product.category = 'Technologie'

    prod_json = data.xpath('//span/@data-affiliate').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.name = prod_json.get('title')
        product.url = prod_json.get('productUrl')

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="article__author"]/text()').string()
    author_url = data.xpath('//a[@class="article__author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="product__note"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0].replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//ul[contains(@class, "positive")])[1]/li//text()').string(multiple=True, normalize_space=False, strip=False)
    if pros:
        for pro in pros.split('\n'):
            pro = pro.strip(' +-*;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//p//text()[contains(., "Les plus :")]').string(multiple=True)
        if pros:
            pros = pros.replace('Les plus :', '').strip(' +-*;•–')
            review.add_property(type='pros', value=pros)

    cons = data.xpath('(//ul[contains(@class, "negative")])[1]/li').string(multiple=True, normalize_space=False, strip=False)
    if cons:
        for con in cons.split('\n'):
            con = con.strip(' +-*;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//p//text()[contains(., "Les moins :")]').string(multiple=True)
        if cons:
            cons = cons.replace('Les moins :', '').strip(' +-*;•–')
            review.add_property(type='cons', value=cons)

    summary = data.xpath('//div[@class="article__introduction"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="product__excerpt"]/p//text()[not(regexp:test(., "Les plus :|Les moins :"))]').string(multiple=True)
    if conclusion:
        conclusion =conclusion.replace('\uFEFF', '').replace('﻿', '').replace('Verdict :', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="article__content"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('\uFEFF', '').replace('﻿', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
