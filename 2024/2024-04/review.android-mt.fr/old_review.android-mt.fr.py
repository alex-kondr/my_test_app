import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('https://www.android-mt.com/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//ul[@id='menu-menu-principal']//li[a[regexp:test(., 'Tests')]]/ul[@class='sub-menu']/li/a"):
        context['category'] = cat.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        cat_url = cat.xpath("@href").string()
        if context['category'] and cat_url:
            session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//div[@class[regexp:test(., 'opinion-posts')]]//article//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = re_search_once('^([^\:]+)', context['name'])
    product.name = product.name.replace('Test du', '').strip()
    product.url = context['url']
    product.category = Category(name = context['category'])
    product.ssid = re_search_once('(\d+)\/*$', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//article[@class[regexp:test(., 'opinion-single')]]//span[@class[regexp:test(., 'meta-date')]]//text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//article[@class[regexp:test(., 'opinion-single')]]//span[@class[regexp:test(., 'meta-author')]]//a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//article[@class[regexp:test(., 'opinion-single')]]//div[@class='entry-content']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//article[@class[regexp:test(., 'opinion-single')]]/div[@class[regexp:test(., 'entry-summary')]]/p//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary))
    for g in data.xpath("//ul[@class='review-list']/li"):
        g_name = g.xpath("span/text()[string-length(normalize-space(.))>0]").string()
        g_value = g.xpath("span//text()[regexp:test(., '\d+\/\d+')]").string()
        if g_name and g_value:
            g_name = g_name.strip('-').strip()
            value, best = re_search_once('(\d+)\/(\d+)', g_value)
            if value and best:
                value = value.replace(',', '.')
                review.grades.append(Grade(name = g_name, value = value, worst = 0, best = best))
    tgrade = data.xpath("//span[@class='review-total-box']/text()[regexp:test(., '\d+\/\d+')]").string()
    if tgrade:
        grade, best = re_search_once('(\d+\.*\d*)\/(\d+)', tgrade)
        if grade and best:
            review.grades.append(Grade(name="Overall", value = grade, worst = 0, best = best, type = 'overall'))

    for pros in data.xpath("//div[@class='review-desc']/h5[regexp:test(., 'Les plus')]/following-sibling::p[1]/text()[string-length(normalize-space(.))>0]"):
        p_value = pros.string()
        if p_value:
            p_value = p_value.strip('►').strip()
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Les plus"))
    for cons in data.xpath("//div[@class='review-desc']/h5[regexp:test(., 'Les moins')]/following-sibling::p[1]/text()[string-length(normalize-space(.))>0]"):
        c_value = cons.string()
        if c_value:
            c_value = c_value.strip('►').strip()
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Les moins"))

    product.reviews.append(review)
    session.emit(product)
