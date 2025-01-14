from agent import *
from models.products import *
import re

def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.bestofrobots.fr/catalog/seo_sitemap/product/'), process_pages, {})

    #url = 'https://www.bestofrobots.fr/mur-virtuel-eziclean-vac100-rouge-accessoires.html'
    #session.queue(Request(url), process_product, dict(context, prUrl=url,prName='prName'))


def process_pages(data, context, session):
    last = data.xpath('//a[@class="last"]//text()').string()
    if last:
        last = int(last) + 1
        for x in xrange(1, last):
            url = 'http://www.bestofrobots.fr/catalog/seo_sitemap/product/?p=' + str(x)
            session.do(Request(url), process_productlist, {})


def process_productlist(data, context, session):
    for cat in data.xpath('//ul[@class="sitemap"]/li/a'):
        prUrl = cat.xpath('@href').string()
        prName = cat.xpath('text()').string(multiple=True)
        if prUrl and prName:
            session.queue(Request(prUrl), process_product, dict(context, prUrl=prUrl, prName=prName))

    #nxtLink = data.xpath('//a[@class="next i-next" and @title="Suivant"]/@href').string()
    #if nxtLink:
    #    session.queue(Request(nxtLink), process_productlist, dict(context))

def process_product(data, context, session):
    pr = Product()
    prName = context['prName']
    pr.name = prName
    prUrl = context['prUrl']
    pr.url = prUrl
    pr.ssid = prUrl.split('/')[-1]
    pr.category = "Robot"

    prManuf = data.xpath('//th[@class="label" and text()="Marque"]/following-sibling::td[1]//text()').string()
    if prManuf:
        pr.manufacturer = prManuf

    if data.xpath('//p[@class="rating-links"]//a//span[@itemprop="ratingCount"]'):
        process_reviews(data, dict(context,pr=pr), session)

    if pr.reviews:
        session.emit(pr)

def process_reviews(data, context, session):
    for rev in data.xpath('//div[@id="product-customer-reviews"]//li'):
        review = Review()
        review.type = 'user'
        review.url = context['pr'].url
        review.ssid = context['pr'].ssid + 'review'

        title = rev.xpath('descendant::span[@class="review-title"]//text()').string()
        if title:
            review.title = title

        revDate=data.xpath('descendant::span[@class="review-by"]/text()[2]').string()
        if revDate:
            revDate = revDate.replace('le','')
            review.date = revDate
            review.ssid += revDate

        revUser = rev.xpath('descendant::span[@class="review-by"]//b//text()').string()
        if revUser:
            review.authors.append(Person(name=revUser, ssid=review.ssid ))
            review.ssid += revUser

        revText = rev.xpath('descendant::div[@class="review_comment"]//text()[string-length(normalize-space(.))>1]').string(multiple=True)
        if revText:
            review.add_property(type='summary', value=revText)

        for gr in rev.xpath('descendant::table[@class="ratings-list"]//tr'):
            grVal= gr.xpath('td[2]//div//@style').string()
            grName = gr.xpath('td[1]//text()[string-length(normalize-space(.))>1]').string()
            if grVal and grName and 'width:' in grVal:
                grVal = grVal.split('width:')[1].split('%;')[0]
                grVal = float(grVal)/20
                review.grades.append(Grade(value=grVal, best = 5, worst=0,name = grName))
            if not grName and grVal and 'width:' in grVal:
                grVal = grVal.split('width:')[1].split('%;')[0]
                grVal = float(grVal)/20
                review.grades.append(Grade(name='Overall Rating', type='overall', value=grVal, best=5, worst=0))

        context['pr'].reviews.append(review)
