import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.queue(Request('http://www.homecinemamagazine.nl/home-cinema-reviews/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class='row-fluid']//div[@class='span6']//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = data.xpath("//span[@class='meta-cat']/a/text()[string-length(normalize-space(.))>0]").string()
    if category:
        category = category.replace(' Reviews', '')
    product.category = Category(name = category)
    product.ssid = re_search_once('\/([^\/]+)\/$', product.url)

    review = Review()
    review.title = context['name'].replace('Review: ', '')
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//span[@class='meta-date']/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//span[@class='meta-author']//a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class='content']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//h2[regexp:test(., 'conclusie', 'i')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusie"))
    for pros in data.xpath("//div[@class='rating-positive']/ul/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pluspunten"))
    for cons in data.xpath("//div[@class='rating-negative']/ul/li"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Minpunten"))
    grade = data.xpath("//div[@class='hReview']//span[@class='value']/text()[regexp:test(., '\d')]").string()
    if grade:
        review.grades.append(Grade(name="Tablets Magazine Beoordeling", value = grade, worst = 0, best = 10, type = 'overall'))
	
    product.reviews.append(review)
    session.emit(product)