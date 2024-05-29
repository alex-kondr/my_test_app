import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.queue(Request('https://www.camerastuffreview.com/lenzen/', use='curl'), process_category, {'category':'Lens'})

def process_category(data, context, session):
    for man in data.xpath("//div[@class='elementor-button-wrapper']/a[@href[regexp:test(., '/lenstest/')]]"):
        manufacturer = man.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        man_url = man.xpath("@href").string()
        if manufacturer and man_url:
            context['manufacturer'] = manufacturer.replace('lenzen', '').strip()
            session.queue(Request(man_url, use='curl'), process_manufacturer, context)

def process_manufacturer(data, context, session):
    for p in data.xpath("//div[@class[regexp:test(., 'elementor-posts-container')]][article]//h6/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url'], use='curl'), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next, use='curl'), process_manufacturer, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = Category(name = context['category'])
    product.ssid = re_search_once('\/([^\/]+)\/*$', product.url)
    product.manufacturer = context['manufacturer']

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//ul[@class[regexp:test(., 'meta')]]/li[@class='meta-date']/text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//ul[@class[regexp:test(., 'meta')]]/li[@class='meta-author']/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//meta[@property='og:description']/@content").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    s_data = data.xpath("//h3[regexp:test(., 'Conclusie')]/following::div[p][1]/p[1]").first()
    if s_data:
        summary = s_data.xpath(".//text()[string-length(normalize-space(.))>0]").string(multiple=True)
        if summary:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusie"))
    for pros in data.xpath("//tr[td/h4[regexp:test(., 'Advantages') or regexp:test(., 'Voordelen', 'i') or regexp:test(., 'Pro')]]/following-sibling::tr[1]/td[1]/ul/li//text()[string-length(normalize-space(.))>0]").strings():
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=pros, name = "Pros"))
    for cons in data.xpath("//tr[td/h4[regexp:test(., 'Disadvantages') or regexp:test(., 'Nadelen', 'i') or regexp:test(., 'Con')]]/following-sibling::tr[1]/td[2]/ul/li//text()[string-length(normalize-space(.))>0]").strings():
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=cons, name = "Cons"))
    grade = data.xpath("//ul[@class='custom-attributes']/li[@class[regexp:test(., 'overall-score')]]//span[@class='attribute-value']/text()[regexp:test(., '\d')]").string()
    if grade:
        review.grades.append(Grade(name="Overall score", value = grade, worst = 0, best = 100, type = 'overall'))
    if excerpt or summary:
        product.reviews.append(review)
        session.emit(product)
