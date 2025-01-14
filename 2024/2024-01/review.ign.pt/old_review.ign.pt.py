import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.queue(Request('https://pt.ign.com/article/review'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class='m']"):
        context['name'] = p.xpath(".//h3/a/text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath(".//h3/a/@href").string()
        context['grade'] = p.xpath("preceding-sibling::div[1][@class='t']//text()[regexp:test(., '\d')]").string()
        if context['name'] and context['url'] and context['grade']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = None
    categories = []
    cats = data.xpath("//div[@class='scoreboxPlatforms']/text()[string-length(normalize-space(.))>0]").string()
    if cats:
        for c in cats.split(','):
            cat = c.strip()
            if not category:
                category = cat
            elif cat != category and not(cat in categories):
                categories.append(cat)
    if not category:
        category = "Movie"
    product.category = Category(name = category)
    product.ssid = re_search_once('\/(\d+)\/', product.url)
    if len(categories) > 0:
        product.also_in = categories

    review = Review()
    review.title = context['name'] 
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='article-publish-date']/span/text()[regexp:test(., '\d\d\d\d')]").string()
    if review.date:
        review.date = re_search_once('^[^\d]+(\d+.+)', review.date)
    if not review.date:
        return
    user_data = data.xpath("//div[@class='article-byline']//span[@class[regexp:test(., 'reviewer')]]/a").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/u\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@id='id_text']/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        ex_data = data.xpath("//div[@id='id_text']//p[.//text()[string-length(normalize-space(.))>100]]").first()
        if ex_data:
                excerpt = ex_data.xpath(".//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        ex_data = data.xpath("//div[@id='id_text']/div[.//text()[string-length(normalize-space(.))>100]]").first()
        if ex_data:
            excerpt = ex_data.xpath(".//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@id='id_text']/text()[string-length(normalize-space(.))>100]").string()
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//h3[@id='id_deck']/text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary))
    conclusion = data.xpath("//div[@class='article-review']//div[@id[regexp:test(., 'bottomline')]]//text()[string-length(normalize-space(.))>0]").string()
    if conclusion:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='conclusion'), value=conclusion, name = "Conclusion"))
    for pros in data.xpath("//ul[@class='pros-cons-list'][@id[regexp:test(., 'pros')]]/li"):
        p_value = pros.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if p_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pros"))
    for cons in data.xpath("//ul[@class='pros-cons-list'][@id[regexp:test(., 'cons')]]/li"):
        c_value = cons.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        if c_value:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Cons"))
    grade = context['grade']
    if grade:
        review.grades.append(Grade(name="Score", value = grade, worst = 0, best = 10, type = 'overall'))
	
    product.reviews.append(review)
    session.emit(product)
