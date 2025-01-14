import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('http://www.channelpostmea.com/category/reviews/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class='entry-content']//h3/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace('Review:', '').strip()
    product.url = context['url']
    product.category = Category(name = "Unknown")
    product.ssid = re_search_once('\/([^\/]+)\/*$', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='heading-post']//time/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//div[@class='heading-post']//a[@rel='author']").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class[regexp:test(., 'body-content')]]/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//div[@class[regexp:test(., 'body-content')]]/p[.//text()[string-length(normalize-space(.))>100]][last()]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusion"))

    product.reviews.append(review)
    session.emit(product)