import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.mytoolstore.de/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//div[@class='menu--container'][div/span[@class='button--category'][regexp:test(., 'Kategorien')]]//ul/li/a"):
        category = cat.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        cat_url = cat.xpath("@href").string()
        if category and cat_url:
            session.queue(Request(cat_url), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//div[@class='listing']/div[@class[regexp:test(., 'product--box')]][.//span[@class='product--rating']]"):
        context['name'] = p.xpath(".//span[@class='product--title']//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("a/@href").string()
        context['ssid'] = p.xpath("@data-ordernumber").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = data.xpath("//a[@class='breadcrumb--link']/@title").join("|") or context['category']
    product.category = Category(name = category)
    product.ssid = product.ssid = re_search_once('(\d+)$', product.url) or context['ssid']
    ean = data.xpath("//meta[@itemprop='gtin13']/@content").string()
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=ean))

    for ur in data.xpath("//body/div[@class='entry--content']"):
        review = Review()
        title = ur.xpath(".//h4[@class='content--title']//text()[string-length(normalize-space(.))>0]").string()
        review.url = product.url
        review.ssid = None
        review.type = 'user'
        review.date = ur.xpath("ancestor::body[1]/preceding-sibling::head[1]/meta[@itemprop='datePublished']/@content").string()
        user = ur.xpath("ancestor::body[1]/preceding-sibling::body[1]//span[@itemprop='author']//text()[string-length(normalize-space(.))>0]").string()
        if user:
            review.authors.append(Person(name = user, ssid = user))
            if review.date:
                review.ssid = product.ssid + '-' + user + '@' + review.date
        grade = ur.xpath("ancestor::body[1]/preceding-sibling::head[2]/meta[@itemprop='ratingValue']/@content").string()
        if grade:
            review.grades.append(Grade(name="Rating", value = grade, worst = 0.5, best = 5, type = 'overall'))
        excerpt = ur.xpath(".//p[@class[regexp:test(., 'review--content')]]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
            review.title = title
        elif title:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=title))

        product.reviews.append(review)

    if product.reviews:
        session.emit(product)
