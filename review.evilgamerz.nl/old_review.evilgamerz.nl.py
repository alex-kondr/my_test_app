import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.queue(Request('http://www.evilgamerz.nl/docs/artikelen.php?sort=alles&type=review&page=1'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//span[@class='tekst_wit']//a[.//span[@class='menu_link']]"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        context['date'] = p.xpath("ancestor::span[@class='tekst_wit']/following-sibling::table[1]//b[regexp:test(., 'Datum')]/following-sibling::text()[string-length(normalize-space(.))>0]").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//a[span/@class='tekst_zwart'][regexp:test(., '^\>$')]/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = "Games"
    platform = data.xpath("//div[@class='menu_link']/span[@class='tekst_wit']/text()[regexp:test(., 'Platform')]/following-sibling::img[1]/@title").string()
    if platform:
        category += '|' + platform
    product.category = Category(name = category)
    product.ssid = re_search_once('(\d+)\.htm', product.url)

    review = Review()
    review.title = data.xpath("//table[@class='news_link']//span[@class='tekst_wit']/span[@style[regexp:test(., 'bold')]]/text()[string-length(normalize-space(.))>0]").string()
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = context['date']
    for pros in data.xpath("//td[@style[regexp:test(., 'bg_plus')]]//text()[string-length(normalize-space(.))>0]"):
        p_value = pros.string()
        if p_value:
            p_value = re_search_once('^..(.+)', p_value)
            if p_value:
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pros"))
    for cons in data.xpath("//td[@style[regexp:test(., 'bg_min')]]//text()[string-length(normalize-space(.))>0]"):
        c_value = cons.string()
        if c_value:
            c_value = re_search_once('^..(.+)', c_value)
            if c_value:
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Cons"))
    grade = data.xpath("//span[text()[regexp:test(., 'Eindcijfer')]]//text()[regexp:test(., '\d')]").string()
    if not grade:
        grade = data.xpath("//td[@background[regexp:test(., 'bg_review')]]/following-sibling::td//text()[regexp:test(., '\d+\.')]").string()
    if grade:
        review.grades.append(Grade(name="Eindcijfer", value = grade, worst = 0, best = 10, type = 'overall'))
    excerpt = data.xpath("//table[@class='news_link']//span[@class='tekst_wit']/text()[string-length(normalize-space(.))>100][1]").string()
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    tuser = data.xpath("//div[@class='menu_link']/span[@class='tekst_wit']/text()[regexp:test(., 'Auteur')]").string()
    if tuser:
        user = re_search_once('\:(.+)', tuser)
        if user:
            review.authors.append(Person(name = user.strip(), ssid = user.strip()))
	
    if grade:
        product.reviews.append(review)
        session.emit(product)