import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('http://www.optyczne.pl/Testy_aparatów_Testy_obiektywów_Testy_lornetek_Inne_testy.html', use='curl', max_age=0), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//ul[@class[regexp:test(., 'tests-nav')]]/li/a"):
        context['category'] = cat.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        cat_url = cat.xpath("@href").string()
        if context['category'] and cat_url:
            session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    tst = data.xpath("//select[@id='producent']/ancestor::form[1]/input[@name='test']/@value").string()
    for man in data.xpath("//select[@id='producent']/option[position()>0]"):
        context['man'] = man.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        man_id = man.xpath("@value").string()
        if context['man'] and man_id:
            man_url = "http://www.optyczne.pl/index.html?test="+tst+"&producent="+man_id+"&przetest=1&szukaj=Wyszukaj"
            session.queue(Request(man_url), process_man, context)

def process_man(data, context, session):
    for p in data.xpath("//div[@class[regexp:test(., 'products-list')]]/div[@class='product']//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = Category(name = context['category'])
    product.ssid = re_search_once('\/(\d+)[^\/]+$', product.url)
    product.manufacturer = context['man']

    review = Review()
    review.ssid = product.ssid
    review.url = product.url
    review.type = 'pro'
    review.date = data.xpath("//div[@class='calendar-date']/text()[string-length(normalize-space(.))>0]").string()
    user = data.xpath("//span[@class[regexp:test(., 'author-link')]]/text()[string-length(normalize-space(.))>0]").string()
    if user:
        review.authors.append(Person(name = user, ssid = user))
    for page in data.xpath("//ul[@class='article-array']/li/a"):
        title = page.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        url = page.xpath("@href").string()
        if title and url:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pages'), value = {'url': url, 'title': title}))
    excerpt = data.xpath("//div[@class='shortcode-content']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='shortcode-content']/text()[string-length(normalize-space(.))>100]").string()
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))

    summary_url = data.xpath("//ul[@class='article-array']/li/a[regexp:test(., 'Podsumowanie')]/@href").string()
    if summary_url:
        session.queue(Request(summary_url), process_summary_page, dict(product=product, review=review))
    else:
        process_summary(data, review)
        product.reviews.append(review)
        session.emit(product)


def process_summary_page(data, context, session):
    review = context['review']
    product = context['product']

    process_summary(data, review)

    product.reviews.append(review)
    session.emit(product)

def process_summary(data, review):
    summary = data.xpath("//h2[regexp:test(., 'Podsumowanie')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not summary:
        summary = data.xpath("//h2[regexp:test(., 'Podsumowanie')]/following-sibling::div[@class='shortcode-content']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not summary:
        summary = data.xpath("//h2[regexp:test(., 'Podsumowanie')]/following-sibling::text()[string-length(normalize-space(.))>0]").string()
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Podsumowanie"))
    for pros in data.xpath("//ul[li][preceding-sibling::*[.//text()[string-length(normalize-space(.))>0]][1][regexp:test(., 'Zalety\:')]]/li/text()[string-length(normalize-space(.))>0]"):
        p_value = pros.string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Zalety"))
    for cons in data.xpath("//ul[li][preceding-sibling::*[.//text()[string-length(normalize-space(.))>0]][1][regexp:test(., 'Wady\:')]]/li/text()[string-length(normalize-space(.))>0]"):
        c_value = cons.string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Wady"))
