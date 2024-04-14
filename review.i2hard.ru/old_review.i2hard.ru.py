import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    sb = SessionBreak()
    sb.max_requests = 7000
    session.sessionbreakers = [ sb ]
    session.queue(Request('http://i2hard.ru/reviews', use='curl'), process_frontpage, {})

XCAT = ['Обзоры']

def process_frontpage(data, context, session):
    for cat in data.xpath("//ul[@class[regexp:test(., 'review-category-list')]]/li/a"):
        context['category'] = cat.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        cat_url = cat.xpath("@href").string()
        if context['category'] and cat_url and not(context['category'] in XCAT):
            session.queue(Request(cat_url, use='curl'), process_category, context)

def process_category(data, context, session):
    for p in data.xpath("//div[@class='news-list']//div[@class='h2']"):
        context['name'] = p.xpath("a//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("a/@href").string()
        context['excerpt'] = p.xpath("following-sibling::p[not(@*)][1]/text()[string-length(normalize-space(.))>0]").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url'], use='curl'), process_product, context)

    next = data.xpath("//a[@id[regexp:test(., 'next_page')]]/@href").string()
    if next:
        session.queue(Request(next, use='curl'), process_category, context)

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = Category(name = context['category'])
    product.ssid = re_search_once('\/([^\/]+)\/*$', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='article-header__info']/span[@class='date']/text()[string-length(normalize-space(.))>0]").string()
    user = data.xpath("//div[@class='article-header__info']/span[@class='author']/text()[string-length(normalize-space(.))>0]").string()
    if user:
        user = user.replace('Автор:', '').strip()
        if user:
            review.authors.append(Person(name = user, ssid = user))
    excerpt = data.xpath("//div[@class='news-detail']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = context['excerpt']
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    else:
        return False
    summary = data.xpath("//div[@class='news-detail']/h2[regexp:test(., '[Ии]тог') or regexp:test(., '[Зз]аключени') or regexp:test(., '[Вв]ывод')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Заключение"))
    for pros in data.xpath("//ul[ancestor::div[@class[regexp:test(., 'news-detail')]]][preceding-sibling::*[1][regexp:test(., 'Достоинства') or regexp:test(., 'Плюсы') or regexp:test(., 'Положительные стороны')]]/li[not(.//script)]"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Плюсы"))
    for cons in data.xpath("//ul[ancestor::div[@class[regexp:test(., 'news-detail')]]][preceding-sibling::*[1][regexp:test(., 'Недостатки') or regexp:test(., 'Минусы') or regexp:test(., 'Недостатки')]]/li[not(.//script)]"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Минусы"))

    product.reviews.append(review)
    session.emit(product)
