import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('https://www.androidworld.nl/review/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class[regexp:test(., '^card')]][a[@class='full-link']]"):
        context['name'] = p.xpath(".//h2/text()[regexp:test(., 'review', 'i')][not(regexp:test(., 'preview', 'i'))]").string()
        context['url'] = p.xpath("a[@class='full-link']/@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//ul[@class[regexp:test(., 'pagination')]]/li[@class='is-active']/following-sibling::li[a[regexp:test(., '\d')]][1]/a/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace('Review ', '').replace('Review: ', '')
    product.url = context['url']
    product.category = Category(name = 'Mobile')
    product.ssid = re_search_once('\/([^\/]+)\/*$', product.url)

    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.url = product.url
    review.type = 'pro'
    review.date = data.xpath("//a[@class[regexp:test(., 'meta__author')]]/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//a[@class[regexp:test(., 'meta__author')]]").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath("span/text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/auteurs\/(.+)\.htm', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class='card-detail-content']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='card-detail-content']/text()[string-length(normalize-space(.))>100]").string()
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    else:
        return False
    summary = data.xpath("//div[@class='card-detail-content']/h2[regexp:test(., 'Conclusie')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not summary:
        summary = data.xpath("//div[@class='card-detail-content']/strong[regexp:test(., 'Conclusie')]/following-sibling::text()[string-length(normalize-space(.))>0]").string()
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusie"))
    has_pros = False
    for pros in data.xpath("//div[@class='card-detail-content']/strong[regexp:test(., 'Pluspunten')]/following-sibling::*[self::ul][1]/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pluspunten"))
            has_pros = True
    if not has_pros:
        for pros in data.xpath("//div[@class='card-detail-content']/h2[regexp:test(., 'Conclusie')]/following-sibling::p[regexp:test(., '^\+')]//text()[regexp:test(., '^\+')]"):
            p_value = pros.string()
            if p_value:
                p_value = p_value.strip('+').strip()
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pluspunten"))
                has_pros = True
    has_cons = False
    for cons in data.xpath("//div[@class='card-detail-content']/strong[regexp:test(., 'Pluspunten')]/following-sibling::*[self::ul][1]/li"):
        c_value = cons.string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Minpunten"))
            has_cons = True
    if not has_cons:
        for cons in data.xpath("//div[@class='card-detail-content']/h2[regexp:test(., 'Conclusie')]/following-sibling::p[regexp:test(., '^\-')]//text()[regexp:test(., '^\-')]"):
            c_value = cons.string()
            if c_value:
                c_value = c_value.strip('-').strip()
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Zwakke punten"))
                has_cons = True

    product.reviews.append(review)
    session.emit(product)
