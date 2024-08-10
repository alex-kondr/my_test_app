import string
from agent import *
from models.products import *
import re

debug = True

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class='obalka']"):
        context['name'] = p.xpath(".//a[@class='contentpagetitle']/text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath(".//a[@class='contentpagetitle']/@href").string()
        context['excerpt'] = p.xpath(".//div[@class='content']/text()[string-length(normalize-space(.))>0]").string()
        context['user'] = p.xpath(".//text()[regexp:test(., 'autor\:')]/following-sibling::a[1]").first()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//a[@title='Další'][img/@src[regexp:test(., 'resultset_next')]]/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {'category': context['category']})

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    category = context['category']
    subcat = data.xpath("//a[@class='pathway'][last()]/text()[string-length(normalize-space(.))>0]").string()
    if subcat:
        category += '|' + subcat
    product.category = Category(name = category)
    product.ssid = re_search_once('\/(\d+)[^\/]+$', product.url)
    review = Review()
    review.ssid = product.ssid
    review.url = product.url
    review.type = 'pro'
    date = data.xpath("//span[@class='createdate']/text()[string-length(normalize-space(.))>0]").string()
    if date:
        review.date = re_search_once('(\d{1,2}\.\d{1,2}\..+)', date)
    has_img = False
    for img in data.xpath("//div[@id='article-text']/p/a[img]"):
        image_src = img.xpath("@href").string()
        image_alt = img.xpath("img/@alt").string()
        if image_src:
            if not image_alt:
                image_alt = product.name
            product.properties.append(ProductProperty(type=ProductPropertyType(name="image"), value = { 'src': image_src, 'alt': image_alt, 'type': 'product'}))
            has_img = True
    if not has_img:
        for img in data.xpath("//div[@id='article-text']/p//img"):
            image_src = img.xpath("@src").string()
            image_alt = img.xpath("@alt").string()
            if image_src:
                if not image_alt:
                    image_alt = product.name
                product.properties.append(ProductProperty(type=ProductPropertyType(name="image"), value = { 'src': image_src, 'alt': image_alt, 'type': 'product'}))
                has_img = True
    title = data.xpath("//div[@id='chapters']//span[@class='active']/text()[string-length(normalize-space(.))>0]").string()
    url = data.request_url
    if title and url:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pages'), value = {'url': url, 'title': title}))
    for page in data.xpath("//div[@id='chapters']//a"):
        title = page.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        url = page.xpath("@href").string()
        if title and url:
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pages'), value = {'url': url, 'title': title}))
    excerpt = data.xpath("//p[@class='perex']/text()[string-length(normalize-space(.))>0]").string()
    if not excerpt:
        excerpt = context['excerpt']
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    user_data = context['user']
    if user_data:
        user = Person()
        user.name = user_data.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        user.profile_url = user_data.xpath("@href").string()
        user.ssid = re_search_once('autor=(\d+)', user.profile_url)
        review.authors.append(user)
    summary_url = data.xpath("//div[@id='chapters']//a[regexp:test(., '[Zz]ávěr')][last()]/@href").string()
    if summary_url:
        context['review'] = review
        context['product'] = product
        session.queue(Request(summary_url), process_summary_page, context)
        return False
    product.reviews.append(review)
    session.emit(product)

def process_summary_page(data, context, session):
    review = context['review']
    product = context['product']
    summary = data.xpath("//div[@id='article-text']/p[not(@*)][.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Závěr"))
    for pros in data.xpath("//tr[td/*[self::strong or self::b][regexp:test(., 'Klady')]]/following-sibling::tr/td[1]/text()[string-length(normalize-space(.))>0]"):
        p_value = pros.string()
        if p_value:
            p_value = re_search_once('^..(.+)', p_value)
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='pros'), value=p_value, name = "Klady"))
    for cons in data.xpath("//tr[td/*[self::strong or self::b][regexp:test(., 'Zápory')]]/following-sibling::tr/td[2]/text()[string-length(normalize-space(.))>0]"):
        c_value = cons.string()
        if c_value:
            c_value = re_search_once('^..(.+)', c_value)
            review.properties.append(ReviewProperty(type=ReviewPropertyType(name='cons'), value=c_value, name = "Zápory"))


    product.reviews.append(review)
    session.emit(product)


def run(context, session): 
    session.queue(Request('http://pctuning.tyden.cz/hardware'), process_frontpage, {'category': 'Hardware'})
    session.queue(Request('http://pctuning.tyden.cz/software'), process_frontpage, {'category': 'Software'})
    session.queue(Request('http://pctuning.tyden.cz/multimedia'), process_frontpage, {'category': 'Multimédia'})
