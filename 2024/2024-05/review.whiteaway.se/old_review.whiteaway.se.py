#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import yaml, simplejson


def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=40000)]
    session.queue(Request('http://www.whiteaway.se/'), process_category, {})

    #url = 'https://www.whiteaway.no/hvitevarer/platetopp/induksjons-platetopp/product/whirlpool-acm-802-ne/review/'
    #session.queue(Request(url), process_product, dict(category='category', url=url, name='name'))

    #url = 'https://www.whiteaway.se/vitvaror/tvattmaskin/frontmatad-tvattmaskin/'
    #session.queue(Request(url), process_productlist, dict(category='name'))


def process_category(data, context, session):
    for view in data.xpath("//ul[contains(@class, 'mega-menu__lvl2')]/li/a"):
        url = view.xpath("(.)/@href").string()
        name = view.xpath("(.)//text()[string-length(normalize-space(.))>1]").join("")
        if url and name:
           session.queue(Request(url), process_productlist, dict(category=name))


def process_productlist(data, context, session):
    jstxt = data.xpath('//script[contains(descendant::text(),"var vueData")]/text()').string()
    if jstxt:
        jstxt = jstxt.replace('var vueData = ','')[:-1]
        prods = simplejson.loads(jstxt)#yaml.load(jstxt)

        for prod in prods['listing']:
            #print type(prod), prod
            name = prod['_1']
            url = prod['_3']
            rated = prod['_4']
            if rated > 0:
                url = 'https://www.whiteaway.se/' + url
                session.queue(Request(url + '/review/'), process_product, dict(context, name=name, url=url))
    else:
        print 'Cant get whole productlist...'
        for view in data.xpath("//div[@class='srp__product-links']/a"):
            url = view.xpath("(.)/@href").string()
            name = view.xpath("(.)//text()[string-length(normalize-space(.))>1]").join("")
            if url and name:
               session.queue(Request(url + 'review/'), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['category']
    product.manufacturer = ''

    if "productId : '" in data.content:
        code = data.content.split("productId : '")[1].split("' });")[0]
        product.ssid = code
        product.add_property(type='id.manufacturer', value=product.ssid)

        revurl = "http://api.bazaarvoice.com/data/batch.json?passkey=lwlek4awxjzijgl7q77uroukt&apiversion=5.5&displaycode=13336-sv_se&filter_reviews.q0=contentlocale:eq:da_DK,no_NO,sv_SE&filter.q0=productid:eq:" + code + "&resource.q0=reviews&sort.q0=relevancy:a1&limit.q0=10"
        print 'PID:', code
        session.do(Request(revurl), process_reviews, dict(product=product, revurl=revurl, cnt=1))
    else:
        print 'No reviews.'

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    offset = context.get('offset', 10)

    jstxt = data.content
    revs = yaml.load(jstxt)
    cnt = 0
    for rev in revs['BatchedResults']['q0']['Results']:
        cnt += 1
        review = Review()
        review.title = rev['Title']
        review.ssid = rev['Id']
        review.url = product.url
        review.type = 'user'

        if rev.get('IsSyndicated'):
            continue

        if rev.get('ProductId') and rev.get('ProductId').lower() != str(product.ssid).lower():
            print 'Review is for another product, original: %s, this: %s' % (rev['ProductId'], str(product.ssid))
            continue

        datetxt = rev['SubmissionTime']
        if datetxt:
            review.date = re_search_once('(\d{4}-\d{2}-\d{2})', datetxt)
        author = rev['UserNickname']
        if not(author):
            author = 'Anonymous'
        if author:
            authorssid = rev['AuthorId']
            review.authors.append(Person(name=author, ssid=authorssid))

        excerpt = rev['ReviewText']
        if excerpt:
            product.reviews.append(review)
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        procons = rev['TagDimensions']
        if procons.has_key('Pro'):
            pros = procons['Pro']['Values']
            for pro in pros:
                review.properties.append(ReviewProperty(type='pros', value=pro))

        if procons.has_key('Con'):
           cons = procons['Con']['Values']
           for con in cons:
               review.properties.append(ReviewProperty(type='cons', value=con))

        score = rev['Rating']
        if score:
            review.grades.append(Grade(name='Rating', type='overall', value=score, best=5))

        if context.get('getSubgrades'):
            for g in rev.get('SecondaryRatings', []):
                review.grades.append(Grade(name=g, type='overall', value=int(rev['SecondaryRatings'][g]['Value']), best=5))

    if cnt == 10:
        revurl = context['revurl'] + '&offset.q0=%s'%(offset+10)
        session.do(Request(revurl), process_reviews, dict(context, offset=offset+10))
