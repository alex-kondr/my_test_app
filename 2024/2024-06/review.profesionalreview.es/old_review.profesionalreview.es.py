import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.profesionalreview.com/category/reviews/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//ul[@id='posts-container']/li//h2/a"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = re_search_once('(.+)[Rr]eview', context['name'])
    if not product.name:
        product.name = context['name'].replace('Video Review: ', '').replace('Review: ', '').replace('Review ', '').replace(' Review', '')
    product.name = product.name.strip()
    product.url = context['url']
    category = "Hardware"
    product.category = Category(name = category)
    txt = data.xpath("//body/@class").string()
    if txt:
        product.ssid = re_search_once('postid\-(\d+)', txt)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='entry-header']//span[@class[regexp:test(., 'date')]]//text()[string-length(normalize-space(.))>0]").string()
    user_data = data.xpath("//div[@class='entry-header']//a[@class='author-name']").first()
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('\/author\/([^\/]+)', user.profile_url)
        review.authors.append(user)
    excerpt = data.xpath("//div[@class[regexp:test(., 'entry-content')]]/p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class[regexp:test(., 'entry-content')]]/p[.//text()[string-length(normalize-space(.))>50]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class[regexp:test(., 'entry-content')]]/div[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0][not(ancestor::script)][not(ancestor::style)]").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    for pros in data.xpath("//tr[td[1][regexp:test(., 'VENTAJAS')]]/following-sibling::tr/td[1]//text()[string-length(normalize-space(.))>0]"):
        p_value = pros.string()
        if p_value:
            p_value = p_value.replace('+', '').strip()
            if p_value:
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Pros"))
    for cons in data.xpath("//tr[td[2][regexp:test(., 'INCONVENIENTES')]]/following-sibling::tr/td[2]//text()[string-length(normalize-space(.))>0]"):
        c_value = cons.string()
        if c_value:
            c_value = re_search_once('^.(.+)', c_value)
            if c_value:
                review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Cons"))
    summary = data.xpath("//div[@class[regexp:test(., 'entry-content')]]/h2[regexp:test(., '[Cc]onclusión')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Conclusion"))
    for g in data.xpath("//div[@id='review-box']/div[@class='review-item']"):
        g_name = g.xpath(".//h5/text()[string-length(normalize-space(.))>0]").string()
        g_value = g.xpath(".//span/@data-width").string()
        if g_name and g_value:
            g_name = re_search_once('(.+)\-', g_name)
            if g_name:
                review.grades.append(Grade(name = g_name.strip(), value = g_value, worst = 0, best = 100))
    grade = data.xpath("//div[@class='review-final-score']/h3/text()[regexp:test(., '\d')]").string()
    if grade:
        review.grades.append(Grade(name="Overall", value = grade, worst = 0, best = 100, type = 'overall'))
    aw = data.xpath("//a[img/@alt[regexp:test(., 'medalla')]]").first()
    if aw:
        name = aw.xpath("img/@alt").string()
        src = aw.xpath("@href").string()
        if name and src:
            product.properties.append(ProductProperty(type=ProductPropertyType(name="awards"), value = {'name': name.replace('-', ' ').title(), 'image_src': src}))

    product.reviews.append(review)
    session.emit(product)
