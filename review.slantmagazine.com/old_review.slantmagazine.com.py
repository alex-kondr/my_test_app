import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    sb = SessionBreak()
    sb.max_requests = 5000
    session.sessionbreakers = [ sb ]
    session.queue(Request('https://www.slantmagazine.com/dvd/', use='curl'), process_category, {'category': 'DVD'})
    session.queue(Request('https://www.slantmagazine.com/games/', use='curl'), process_category, {'category': 'GAMES'})
    session.queue(Request('https://www.slantmagazine.com/film/', use='curl'), process_category, {'category': 'Film'})

def process_category(data, context, session):
    for p in data.xpath("//ul[@class[regexp:test(., 'mvp-blog-story-list')]]/li"):
        context['name'] = p.xpath(".//h2[regexp:test(., 'Review', 'i')]//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("a/@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url'], use='curl'), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next, use='curl'), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = context['category']
    subcat = data.xpath("//div[@id='mvp-content-main']/p[@class='docent_acf_display_credits']//strong[regexp:test(., 'Platform')]/following-sibling::text()[string-length(normalize-space(.))>0][1]").string()
    if subcat:
        category += '|' + subcat
    product.category = Category(name = category)
    product.ssid = re_search_once('slantmagazine.com\/(.+)', product.url)
    if product.ssid:
        product.ssid = product.ssid.replace('/', '-')

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//span[@class[regexp:test(., 'mvp-post-date')]]//time/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//header[@id='mvp-post-head']//span[@class[regexp:test(., 'author-name')]]//a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    grade = data.xpath("//header[@id='mvp-post-head']//span[@itemprop='ratingValue']/text()[regexp:test(., '\d+\.*\d*')]").string()
    if grade:
        review.grades.append(Grade(name="Rating", value = grade, worst = 0, best = 5, type = 'overall'))
    excerpt = data.xpath("//div[@id='mvp-content-main']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))

        product.reviews.append(review)
        session.emit(product)
