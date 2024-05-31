import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('http://blog.gamerstuff.fr/category/tests/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@id='primary-left']//article//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = re_search_once('^(.+) –', context['name'])
    if product.name:
        product.name = product.name.replace('Test : ', '').replace('Test ', '')
    else:
        product.name = context['name'].replace('Test : ', '').replace('Test ', '')
    product.url = context['url']
    category = data.xpath("//span[@class='post-category']/a[not(regexp:test(., 'Tests / Comparatifs'))]/text()[string-length(normalize-space(.))>0]").string()
    if category:
        category = category.replace('Tests', '').strip()
    product.category = Category(name = category)
    ssid = data.xpath("//body/@class").string()
    if ssid:
        product.ssid = re_search_once('postid\-(\d+)', ssid)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//article/div[@class='entry-meta']/span[@class[regexp:test(., 'post-date')]]/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//article/div[@class='entry-meta']/span[@class[regexp:test(., 'post-author')]]/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class='post-content']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//div[@class='post-content']//h2[regexp:test(., 'Conclusion', 'i')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusion"))
    grade = data.xpath("//article//span[@itemprop='ratingValue']/text()[regexp:test(., '\d+')]").string()
    if grade:
        review.grades.append(Grade(name="Rating", value = grade, worst = 0, best = 100, type = 'overall'))
    for g in data.xpath("//div[@id='review-box']/div[@class='review-item']"):
        g_name = re_search_once('^(.+).\-', g.xpath(".//h5/text()[string-length(normalize-space(.))>0]").string())
        g_value = g.xpath(".//span/@data-width").string()
        if g_name and g_value:
            review.grades.append(Grade(name = g_name, value = g_value, worst = 0, best = 100))
    for pros in data.xpath("//div[@class='review-col-more'][p[regexp:test(., 'plus')]]/ul/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Les plus"))
    for cons in data.xpath("//div[@class='review-col-more'][p[regexp:test(., 'moins')]]/ul/li"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Les plus"))

    product.reviews.append(review)
    session.emit(product)