import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('http://www.gameforfun.com.br/reviews/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class[regexp:test(., 'jeg_heroblock')]]//article//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    for p in data.xpath("//div[@class[regexp:test(., 'jeg_main_content')]]//article//h3/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = get_category(product.name)
    product.category = Category(name = category)
    ssid = data.xpath("//div[@id='post-body-class']/@class").string()
    if ssid:
        product.ssid = re_search_once('postid\-(\d+)', ssid)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='entry-header']//div[@class='jeg_meta_date']//text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//div[@class='entry-header']//div[@class='jeg_meta_author']/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class[regexp:test(., 'content-inner')]]/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        ex_data = data.xpath("//div[@class[regexp:test(., 'content-inner')]]//p[.//text()[string-length(normalize-space(.))>100]][1]").first()
        if ex_data:
            excerpt = ex_data.xpath(".//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    for page in data.xpath("//ul[@class='jeg_splitpost_nav']/li/a"):
        title = page.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        url = page.xpath("@href").string()
        if title and url:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pages'), value = {'url': url, 'title': title}))
    summary_url = data.xpath("//ul[@class='jeg_splitpost_nav']/li[a][last()]/a/@href").string()
    if summary_url:
        session.queue(Request(summary_url), process_summary_page, dict(product=product, review=review))
    else:
        process_summary(data, review)

        product.reviews.append(review)
        session.emit(product)

def process_summary_page(data, context, session):
    product = context['product']
    review = context['review']

    process_summary(data, review)

    product.reviews.append(review)
    session.emit(product)

def process_summary(data, review):
    summary = data.xpath("//div[@class='jeg_review_wrap']//div[@class='desc']/p//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusion"))
    for pros in data.xpath("//div[@class='conspros'][h3[regexp:test(., 'PRÓS')]]/ul/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "PRÓS"))
    for cons in data.xpath("//div[@class='conspros'][h3[regexp:test(., 'CONTRA')]]/ul/li"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "CONTRA"))
    grade = data.xpath("//div[@class='jeg_review_wrap']//span[@class='score_value']/text()[regexp:test(., '\d')]").string()
    if grade:
        if float(grade) > 10:
            grade = str(float(grade)/10)
        review.grades.append(Grade(name="Pontuação", value = grade, worst = 0, best = 10, type = 'overall'))
    for g in data.xpath("//div[@class[regexp:test(., 'jeg_reviewscore')]]/ul/li"):
        g_name = g.xpath("strong/text()[string-length(normalize-space(.))>0]").string()
        g_value = g.xpath(".//span[@class='barbg']/@data-width").string()
        if g_name and g_value:
            review.grades.append(Grade(name = g_name, value = str(float(g_value)/10), worst = 0, best = 10))


def get_category(title):
    if re_search_once('(PS4)', title):
        return 'PS4'
    elif re_search_once('(Xbox One)', title):
        return 'Xbox One'

    return 'Videogames'