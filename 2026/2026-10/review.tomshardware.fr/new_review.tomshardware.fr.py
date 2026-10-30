from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.tomshardware.fr/category/test/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('Mini test :', '').replace('Test :', '').split(' : ')[0].split(' en test')[0].split(' et test')[0].replace('Test ', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('test-', '')
    product.category = 'Technologie'

    try:
        prod_json = data.xpath('//span/@data-affiliate').string()
        prod_json = simplejson.loads(prod_json)

        product.name = prod_json.get('title')
        product.url = prod_json.get('productUrl')

        ean = prod_json.get('gtin')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//div[contains(@class, "meta__detail")]/time/@datetime').string()

    if date:
        review.date = date.split()[0].split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    author_url = data.xpath('//a[@class="article__author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="product__note"]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0].replace(',', '.')
        if grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//ul[contains(@class, "positive")])[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//p//text()[contains(., "Les plus :")]').string(multiple=True)
        if pros:
            pros = pros.replace('Les plus :', '').strip(' +-*;•–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

    cons = data.xpath('(//ul[contains(@class, "negative")])[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//p//text()[contains(., "Les moins :")]').string(multiple=True)
        if cons:
            cons = cons.replace('Les moins :', '').strip(' +-*;•–')
            if len(cons) > 1:
                review.add_property(type='cons', value=cons)

    summary = data.xpath('//div[@class="article__introduction"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="product__excerpt"]/p//text()[not(regexp:test(., "Les plus :|Les moins :"))]').string(multiple=True)

    if conclusion:
        conclusion =conclusion.replace('\uFEFF', '').replace('﻿', '').replace('Verdict :', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article__content")]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace('\uFEFF', '').replace('﻿', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)