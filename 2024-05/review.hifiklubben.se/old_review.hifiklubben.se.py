# -*- coding: utf8 -*-
from agent import *
from models.products import *

import simplejson
import datetime


def run(context, session):
    #session.browser.use_new_parser = True
    session.queue(Request('https://www.hifiklubben.se', use="curl"), process_first_page, {})

    #url = 'https://www.hifiklubben.no/api/v2/content/streaming/bluesound/facetsearch/?page=0&host=www.hifiklubben.no'
    #session.queue(Request(url, use="curl"), process_productlistJSON, dict(category='category', page=0, base_url=url))
    #url = 'https://www.hifiklubben.no/api/v2/content/tilbehor/mobler/facetsearch/?page=2&host=www.hifiklubben.no'
    #session.queue(Request(url, use="curl"), process_productlistJSON, dict(category='category', page=2, base_url=url))


def process_first_page(data, context, session):
    for link in data.xpath('//ul[contains(@class,"navigation-menu")]//a'):
        url = link.xpath('@href').string()
        category = link.xpath('text()').string()
        if url and category:
            #session.queue(Request(url, use="curl"), process_category, dict(category=category))

            url = 'https://www.hifiklubben.se/api/v2/content/' + url.split('.hifiklubben.se/')[1] + 'facetsearch/?page=0&host=www.hifiklubben.se'
            session.queue(Request(url, use="curl"), process_productlistJSON, dict(category=category, page=0, base_url=url))


def process_productlistJSON(data, context, session):
    cnt = 0
    jstxt = data.content
    if jstxt[0:2]=='{}': jstxt = jstxt.replace('{}','', 1)
    jstxt = jstxt.replace(',"energySpecifications":{}','')

    print jstxt
    if 'The resource you are looking for' in jstxt: return
    prods = simplejson.loads(jstxt)

    for prod in prods['filteredItems']:
        cnt += 1
        name = prod['brandName']
        name2 = prod.get('modelType', False)
        name3 = prod.get('modelName', False)

        url = 'https://www.hifiklubben.se' + prod['url']
        sku = prod['skuCode']
        if url and name:
            if not name3 == 1: name3 = sku
            if not name2:
                name = name + ' ' + name3
            else:
                name = name + ' ' + name2 + ' ' + name3

            session.queue(Request(url, use="curl"), process_product, dict(context, url=url, name=name))

    if cnt == 24:
        page = context['page'] + 1
        url = context['base_url'].replace('page=0','page='+str(page))
        session.do(Request(url, use="curl"), process_productlistJSON, dict(context, page=page))


def process_category(data, context, session):
    for link in data.xpath('//div[@class="product-card__brand-name"]'):
        url=link.xpath('a//@href').string()
        name=link.xpath('descendant::text()').string(multiple=True)
        if url and name:
            session.queue(Request(url, use="curl"), process_product, dict(context, url=url, name=name))


def process_product(data, context, session):
    product=Product()
    product.name=context['name']
    product.url=context['url']
    product.ssid=product.name
    product.category=context['category']

    # Brand
    brand = data.xpath('//h1//span[contains(@class,"brand")]//text()').string()
    if brand:
        product.manufacturer=brand

    review=Review()
    review.product=product.name
    review.url=product.url
    review.ssid=product.ssid + ' review'
    review.type='pro'

    is_rev = False

    # Publish date
    review.date='unknown'

    # Author
    review.authors.append(Person(name='hifiklubben', ssid='hifiklubben'))

    # Excerpt
    excerpt=data.xpath('//div[@id="description"]//h3//text()').string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt',value=excerpt[:333]+'...'))

    # Pros
    for p in data.xpath('//ul[contains(@class,"__list--long")]//li'):
        pros=p.xpath('descendant::text()').string()
        if pros:
            is_rev = True
            review.properties.append(ReviewProperty(type='pros',value=pros))

    # Cons
    for c in data.xpath('//ul[contains(@class,"__list--short")]//li'):
        cons=c.xpath('descendant::text()').string()
        if cons:
            is_rev = True
            review.properties.append(ReviewProperty(type='cons',value=cons))

    if is_rev:
        product.reviews.append(review)

    # USER REVIEWS
    for link in data.xpath('//div[@class="reviews"]//article[@class="reviewItem"]'):
        review=Review()
        review.product=product.name
        review.url=product.url
        review.type='user'
        review.ssid=product.ssid

        # Publish date
        pdate = link.xpath('descendant::p[@class="reviewDate"]//text()').string()
        if pdate:
            if 'Én vecka' in pdate:
                review.date=str(datetime.datetime.now()-datetime.timedelta(weeks=1))[:-16]
            elif ' dagar ' in pdate:
                xdate = int(pdate.split(' dagar ')[0])
                review.date=str(datetime.datetime.now()-datetime.timedelta(days=xdate))[:-16]
            elif ' veckor ' in pdate:
                xdate = int(pdate.split(' veckor ')[0])
                review.date=str(datetime.datetime.now()-datetime.timedelta(weeks=xdate))[:-16]
            elif 'Én månad' in pdate:
                review.date=str(datetime.datetime.now()-datetime.timedelta(weeks=4))[:-16]
            elif ' månader ' in pdate:
                xdate = int(pdate.split(' månader ')[0])*4
                review.date=str(datetime.datetime.now()-datetime.timedelta(weeks=xdate))[:-16]
            else:
                print pdate
                review.date='unknown'
        else:
            review.date='unknown'

        # Author
        author=link.xpath('descendant::p[@class="reviewerName"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))
        else:
            review.authors.append(Person(name='unknown', ssid='unknown'))

        # Grades
        count = 0
        for g in link.xpath('descendant::div//span[@class="icon-star"]'):
            star = g.xpath('@class').string()
            count +=1

        if count > 0:
            score = float(count)
            review.grades.append(Grade(name='Overall Rating', type='overall', value=score, best=5))

        # Summary
        summary = link.xpath('descendant::p[@class="reviewText"]//text()').string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type='summary', value=summary))

        if summary:
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
