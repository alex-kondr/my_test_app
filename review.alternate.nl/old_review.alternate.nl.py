#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *

XCAT = ['Cartridges','Toners','Drumkits', 'Papier & Folie', 'Printkoppen', 'Inktbanden', 'Toebehoren',
'Blanco Media', 'Blu-ray discs', 'Controllers', 'Kabels', 'Beschermhoesjes', 'Screenprotectors', 'Toebehoren', 'Verlichting', 'Speelgoed']

seen_urls = []


import agent
def request(url):
    r = agent.Request(url, max_age=0, use='curl')
    r.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3')
    r.add_header('Upgrade-Insecure-Requests', '1')
    r.add_header('Cache-Control', 'max-age=0')
    r.add_header('Connection', 'keep-alive')
    r.add_header('Sec-Fetch-Mode', 'navigate')
    r.add_header('Sec-Fetch-Site', 'none')
    r.add_header('Sec-Fetch-User', '?1')
    r.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36')
    r.add_header('X-Compress', 'null')
    r.add_header('cookie', 'JSESSIONID=IqAIGgKnWB0ZI6VWI8jxd6G2PHbJQUMMnA4KooY1.15; __cf_bm=1011c9ebdd3a476633c4f7cba94be10662b1e1e7-1627426030-1800-ARlswXVvMS3moD9d01zRCSx8nbfVY5h4QPW1N+276CHgtHK7fKEpP+hK+ateDUsnlpAWPtU2RsCzosmKin+NM0s=; permanent=7078baa9f1cd46493f67cbb4d759217b23faed74304dfe274cfc77da6ac6a; TLECookieAcceptance={"v":4,"r":1,"p":1,"s":1,"m":1}; _ga=GA1.2.823414807.1627426137; _gid=GA1.2.923057302.1627426137; _gcl_au=1.1.246056708.1627426137; _gat=1; _gat_UA-473831-14=1')

    return r

Request = request


def run(context, session):
   session.sessionbreakers = [SessionBreak(max_requests=15000)]
   session.browser.agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2209.0 Safari/537.36'
   session.queue(Request('https://www.alternate.nl/html/index.html'), process_index, {})

   #url = 'https://www.alternate.nl/Notebook/Gaming'
   #session.queue(Request(url), process_productlist, dict(context,catName='123'))
   run_facebook(context, session)


def run_facebook(context, session):
    context['set_rating'] = True
    session.sessionbreakers = [SessionBreak(max_requests=15000)]
    session.browser.agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2209.0 Safari/537.36'

    url = 'https://www.alternate.nl/Gaming/VR-brillen'
    session.queue(Request(url), process_preproductlist, dict(context, catUrl=url, catName='VR-brillen'))


def process_index(data, context, session):
    print data.content
    for cat in data.xpath('//div[@id="navigation-tree"]/div[1]//a'):
        catName = cat.xpath('text()').string(multiple=True)
        catUrl = cat.xpath('@href').string()
        if catName and catUrl:
            session.queue(Request(catUrl), process_cat, dict(context, catUrl=catUrl, catName=catName))


def process_cat(data, context, session):
    have_cats = False

    for cat in data.xpath('//span[@id="tle-tree-navigation:navigation-form:children:0:sub-tree"]/following-sibling::ul[1]//a'):
        catName = cat.xpath('.//text()').string(multiple=True)
        if catName in XCAT: continue
        catUrl = cat.xpath('@href').string()
        if catName and catUrl and catUrl not in seen_urls:
            have_cats = True
            seen_urls.append(catUrl)

            session.queue(Request(catUrl), process_cat, dict(context, catUrl=catUrl))

    if not have_cats:
        for cat in data.xpath('//span[@class="text-primary font-weight-bold cursor-pointer"]/following-sibling::ul[1]//a'):
            catName = cat.xpath('descendant::text()').string(multiple=True)
            if catName in XCAT: continue
            catUrl = cat.xpath('@href').string()
            if catName and catUrl and catUrl not in seen_urls:
                have_cats = True
                seen_urls.append(catUrl)

                session.queue(Request(catUrl), process_cat, dict(context, catUrl=catUrl))

    if not have_cats:
        for cat in data.xpath('//li[@class="mt-2"]/a'):
            catName = cat.xpath('descendant::text()').string(multiple=True)
            if catName in XCAT: continue
            catUrl = cat.xpath('@href').string()
            if catName and catUrl and catUrl not in seen_urls:
                have_cats = True
                seen_urls.append(catUrl)

                session.queue(Request(catUrl), process_cat, dict(context, catUrl=catUrl))

    if not have_cats:
        print 'NO CATS?', data.response_url
        session.queue(Request(data.response_url), process_preproductlist, dict(context))


def process_preproductlist(data, context, session):
    cid = data.xpath('//input[@name="t"]//@value').string()
    if cid:
        url = 'https://www.alternate.nl/listing_ajax.xhtml?&t=' + cid + '&af=true&listing=0&s=rating_asc&page=1'
        session.queue(Request(url), process_productlist, dict(context, base_url=url, page=1))


def process_productlist(data, context, session):
    cnt = 0
    for cat in data.xpath('//a[following-sibling::div[1][descendant::span[@class="ratingCount pl-1"]]]'):
        prUrl = cat.xpath('@href').string()
        prName = cat.xpath('following-sibling::div[1]//div[contains(@class, "product-name ")]//text()').string(multiple=True)
        if prUrl and prName:
            cnt += 1
            session.queue(Request(prUrl), process_product, dict(context, prUrl=prUrl, prName=prName))

    if cnt > 0:
        page = context['page'] + 1
        url = context['base_url'].replace('page=1','page='+str(page))
        session.queue(Request(url), process_productlist, dict(context, page=page))


def process_product(data, context, session):
    pr = Product()
    pr.name = context['prName']
    pr.url = context['prUrl']
    pr.ssid = context['prUrl'].split("/")[-1]
    pr.sku = data.xpath('//meta[@itemprop="sku"]//@content').string()

    category = data.xpath('//li[contains(@class,"breadcrumb-item ")]//text()[string-length(normalize-space(.))>1]').join('|')
    if category:
        pr.category = category
    else:
        pr.category = context['catName']

    revUrl = pr.url.replace('/product/','/productRatings/') + '?p=' + pr.ssid + '&rating=1&stars=-1&s=DATEDESC'
    if revUrl:
        session.do(Request(revUrl), process_reviews, dict(context, pr=pr))

    if pr.reviews:
        session.emit(pr)


def process_reviews(data, context, session):
    rating_value = data.xpath('//meta[@itemprop="ratingValue"]//text()').string()
    review_count = data.xpath('//meta[@itemprop="ratingCount"]//text()').string()
    if context.get('set_rating') and rating_value and review_count:
        product.set_rating(rating_value=rating_value, review_count=review_count, rating_count=review_count)

    for rev in data.xpath('//div[contains(@class, "card ratingBox")]'):
        review = Review()
        review.type = 'user'
        review.url = context['pr'].url
        review.ssid = rev.xpath('descendant::input//@value').string()

        revUser = rev.xpath('following::body[1]//span[@itemprop="name"]/text()[string-length(normalize-space(.))>1]').string()
        if revUser:
            revUser = revUser.replace('review door','')
            review.authors.append(Person(name=revUser, ssid=revUser ))
        else:
            review.authors.append(Person(name='unknown', ssid='unknown' ))

        revDate = rev.xpath('following::body[1]//span[@itemprop="dateCreated"]//text()').string()
        if revDate:
            #revDate=revDate.split(' ')[-1]
            review.date = revDate
        else:
            review.date = 'unknown'

        if not review.ssid and revUser:
            review.ssid = revUser + review.date

        revText = rev.xpath('following::body[1]//span[@itemprop="description"]//text()').string(multiple=True)
        if revText:
            review.add_property(type='summary', value=revText)

        revGrade = rev.xpath('following::head[1]//meta[@itemprop="ratingValue"]//@value').string()
        if revGrade:
            review.grades.append(Grade(type='overall', name='Customer Rating', value=float(revGrade), best=5.0))

        context['pr'].reviews.append(review)

    #next?
    nxtLink = data.xpath('//div[@class="paging"]//a[@class="next"]//@href').string()
    if nxtLink:
        session.do(Request(nxtLink), process_reviews, dict(context))
