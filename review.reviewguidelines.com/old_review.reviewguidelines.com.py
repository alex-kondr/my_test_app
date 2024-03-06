import string
from agent import *
from models.products import *
import re

debug = True

XCAT = ['Guide']

def run(context, session): 
    session.browser.agent = "Firefox"
    session.browser.use_new_parser = True   
    session.queue(Request('http://www.reviewguidelines.com/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//ul[@id='menu-mainmenu']/li"):
        category = cat.xpath("a//text()[string-length(normalize-space(.))>0]").string()
        if category in XCAT:
            continue
        cat_url = cat.xpath("a/@href").string()
        has_sub = False
        for sub in cat.xpath("ul/li/a"):
            subcat = sub.xpath(".//text()[string-length(normalize-space(.))>0]").string()
            sub_url = sub.xpath("@href").string()
            if sub_url and subcat: 
                context['category'] = category + '|' + subcat
                session.queue(Request(sub_url), process_category, context)
                has_sub = True
        if not has_sub and category and cat_url:
            context['category'] = category
            session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//ul[@class='posts-items']/li"):
        context['name'] = p.xpath(".//h2/a//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath(".//h2/a/@href").string()
        context['date'] = p.xpath(".//span[@class[regexp:test(., 'date')]]/text()[string-length(normalize-space(.))>0]").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//ul[@class='pages-numbers']/li[@class='current']/following-sibling::li[a[regexp:test(., '\d')]][1]/a/@href").string()
    if next:
        session.queue(Request(next), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace('Review – ', '').replace(' – Review', '').replace(': Review', '').replace(' Review', '')
    product.url = context['url']
    product.category = Category(name = context['category'])
    ssid = data.xpath("//body[@id='tie-body']/@class").string()
    if ssid:
        product.ssid = re_search_once('(\d+)', ssid)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = context['date']
    excerpt = data.xpath("//div[@class[regexp:test(., 'entry-content')]]/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//div[@class[regexp:test(., 'entry-content')]]/*[not(self::p)][regexp:test(., 'Conclusion')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusion"))
    pros = data.xpath("//div[@class='review-summary']//strong[regexp:test(., 'PROS')]/following-sibling::text()[string-length(normalize-space(.))>0][1]").string()
    if pros:
        for p_value in pros.split(','):
            if p_value:
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value.strip(), name = "Pros"))
    cons = data.xpath("//div[@class='review-summary']//strong[regexp:test(., 'CONS')]/following-sibling::text()[string-length(normalize-space(.))>0][1]").string()
    if cons:
        for c_value in cons.split(','):
            if c_value:
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value.strip(), name = "Cons"))
    for g in data.xpath("//div[@id='review-box']/div[@class='review-item']"):
        g_name = g.xpath("h5/text()[string-length(normalize-space(.))>0]").string()
        g_value = g.xpath(".//span/@style").string()
        if g_name and g_value:
            g_value = re_search_once('width\s*\:\s*(\d+\.*\d*)', g_value)
            if g_value:
                review.grades.append(Grade(name = g_name, value = str(float(g_value)/20), worst = 0, best = 5))
    grade = data.xpath("//div[@class='review-final-score']//span/@style").string()
    if grade:
        grade = re_search_once('width\s*\:\s*(\d+\.*\d*)', grade)
        if grade:
            review.grades.append(Grade(name="Overall score", value = str(float(grade)/20), worst = 0, best = 5, type = 'overall'))

    product.reviews.append(review)
    session.emit(product)