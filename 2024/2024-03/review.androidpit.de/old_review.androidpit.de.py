import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.queue(Request('https://www.androidpit.de/tests'), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//li[@id='navbar-reviews']//li[h3[regexp:test(., 'Ger.te')]]/ul/li/a"):
        context['category'] = cat.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        cat_url = cat.xpath("@href").string()
        if context['category'] and cat_url:
            session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//div[@class='articleTeaserContent']//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = re_search_once('^(.+)\:', context['name'])
    if product.name:
        product.name = product.name.replace(' im Test', '').strip()
    else:
        product.name = context['name']
    product.url = context['url']
    product.category = Category(name = context['category'].replace('Tests', '').strip())
    product.ssid = re_search_once('\/([^\/]+)\/*$', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='articleAuthor']//time/@datetime").string()
    user_data = data.xpath("//div[@class='articleAuthor']/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//span[@class='articleAuthorLinkText']/text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/user\/(\d+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class='articlePartIntroContent']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    tgrade = data.xpath("//span[@class='ratingStars']/use/@xlink_href").string()
    if tgrade:
        grade = re_search_once('rating\-stars\-(\d+)', tgrade)
        if grade:
            review.grades.append(Grade(name="Bewertung", value = str(float(grade)/2), best = 5, type = 'overall'))
    summary = data.xpath("//div[@itemprop='description']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not summary:
        summary = data.xpath("//div[@class='finalVerdictDesc']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Fazit"))
    for pros in data.xpath("//div[@class='reviewGood']//span[@class='goodBadContent']/text()[string-length(normalize-space(.))>0]"):
        p_value = pros.string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pro"))
    for cons in data.xpath("//div[@class='reviewBad']//span[@class='goodBadContent']/text()[string-length(normalize-space(.))>0]"):
        c_value = cons.string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Contra"))

	
    product.reviews.append(review)
    session.emit(product)