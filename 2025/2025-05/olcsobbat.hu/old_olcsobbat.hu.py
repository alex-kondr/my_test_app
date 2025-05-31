import string
from agent import *
from models.products import *
import re

debug = True


def run(context, session):
    sb = SessionBreak()
    sb.max_requests = 10000
    session.sessionbreakers = [ sb ]
    session.browser.use_new_parser = True
    session.queue(Request('http://www.olcsobbat.hu/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for t in data.xpath("//nav[@id='mainMenu']/ul/li"):
        topcat = t.xpath("span/text()[string-length(normalize-space(.))>0]").string()
        for cat in t.xpath("ul/li"):
            category = cat.xpath("span/text()[string-length(normalize-space(.))>0]").string()
            for sub in cat.xpath(".//ul/li/a"):
                subcat = sub.xpath(".//text()[string-length(normalize-space(.))>0]").string()
                cat_url = sub.xpath("@href").string()
                if subcat and cat_url and topcat and cat_url:
                    context['category'] = topcat + '|' + category + '|' + subcat
                    session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//div[@class='infoColumn'][.//span[@class[regexp:test(., 'glyphicon')][regexp:test(., 'selected')]]]//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url'] + '/velemenyek.html'), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = Category(name = context['category'])
    product.ssid = product.name

    process_reviews(data, product)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_next_page, dict(product=product))
    else:
        if product.reviews:
            session.emit(product)

def process_next_page(data, context, session):
    product = context['product']

    process_reviews(data, product)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_next_page, dict(product=product))
    else:
        if product.reviews:
            session.emit(product)


def process_reviews(data, product):
    for ur in data.xpath("//div[@class='reviewBlock']/div[@class='review']"):
        review = Review()
        ssid = ur.xpath("@id").string()
        if ssid:
            review.ssid = ssid.replace('review_', '')
        review.url = product.url
        review.type = 'user'
        review.date = ur.xpath(".//div[meta[@itemprop='datePublished']]/text()[string-length(normalize-space(.))>0]").string()
        user = ur.xpath(".//div[@itemprop='author']/text()[string-length(normalize-space(.))>0]").string()
        if not user:
            user = "Anonymous"
        if user:
            review.authors.append(Person(name = user, ssid = user))
        grade = len(ur.xpath(".//span[@class='ratingWidget']/span[@class[regexp:test(., 'selected')]]"))
        if grade:
            review.grades.append(Grade(name="Rating", value = grade, worst = 0, best = 5, type = 'overall'))
        excerpt = ur.xpath(".//p[@id[regexp:test(., 'datasheetReviewComment')]]/text()[string-length(normalize-space(.))>0]").string()
        if excerpt:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
        else:
            continue
        p_value = ur.xpath(".//div/p/text()[string-length(normalize-space(.))>0][preceding-sibling::b[1][regexp:test(., 'Pozitív')]]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pozitív"))
        c_value = ur.xpath(".//div/p/text()[string-length(normalize-space(.))>0][preceding-sibling::b[1][regexp:test(., 'Negatív')]]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Negatív"))

        product.reviews.append(review)