import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.dehner.de/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//ul[@class='nav-level-0']/li"):
        category = cat.xpath("a/text()[string-length(normalize-space(.))>0]").string()
        for sub in cat.xpath("div/ul/li/a[not(regexp:test(., 'Marken'))]"):
            subcat = sub.xpath(".//text()[string-length(normalize-space(.))>0]").string()
            cat_url = sub.xpath("@href").string()
            if category and subcat and cat_url:
                context['category'] = category + '|' + subcat
                session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//div[@class[regexp:test(., 'product-list')]]/div[@class[regexp:test(., 'product-card')]][.//span[@itemprop='ratingValue']]//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = Category(name = context['category'])
    product.ssid = product.ssid = re_search_once('-([^\-]+)\/*$', product.url)
    product.manufacturer = data.xpath("//div[@class[regexp:test(., 'product-brand-icon')]]/img/@alt").string()

    for ur in data.xpath("//ul[@id='ratings-list']/li"):
        review = Review()
        review.url = product.url
        review.ssid = None
        review.type = 'user'
        review.date = ur.xpath(".//span[@class='rating-meta-date']/text()[string-length(normalize-space(.))>0]").string()
        user = ur.xpath(".//span[@class='rating-meta-name']/text()[string-length(normalize-space(.))>0]").string()
        if user:
            review.authors.append(Person(name = user, ssid = user))
            if review.date:
                review.ssid = product.ssid + '-' + user + '@' + review.date
        grade = ur.xpath(".//span[@class='icon-star-background']/@style").string()
        if grade:
            grade = re_search_once('width\s*\:\s*(\d+)', grade)
            if grade:
                grade = str(float(grade)/20)
                if grade:
                    review.grades.append(Grade(name="Rating", value = grade, best = 5, type = 'overall'))
        excerpt = ur.xpath(".//div[@class='rating-content']/text()[string-length(normalize-space(.))>0]").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))

        product.reviews.append(review)

    if product.reviews:
        session.emit(product)