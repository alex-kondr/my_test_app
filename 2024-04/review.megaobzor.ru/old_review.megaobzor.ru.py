import string
from agent import *
from models.products import *
import re

debug = True

def run(context, session): 
    session.browser.use_new_parser = True
    session.queue(Request('http://megaobzor.com/news-topic-15-page-1.html'), process_frontpage, {})

def process_frontpage(data, context, session):
    for p in data.xpath("//div[@class='n_links3-part-ins']/ul/li//a[b]"):
        context['name'] = p.xpath(".//text()[string-length(normalize-space(.))>0]").string()
        context['url'] = p.xpath("@href").string()
        if context['name'] and context['url']:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//center/button[regexp:test(., '\d')]/following-sibling::a[regexp:test(., '\d')][@href[regexp:test(., 'page\-\d')]][1]/@href").string()
    if next:
        session.queue(Request(next), process_frontpage, {})

def process_product(data, context, session):
    product = Product()
    product.name = context['name'].replace('Обзор и тесты', '')
    product.name = re_search_once('^(.+)\.[^\.]+$', product.name)
    if not product.name:
        product.name = context['name']
    product.name = product.name.replace('Обзор и тесты', '').replace('Обзоры и тесты', '')
    product.name = product.name.strip()

    product.url = context['url']
    category = data.xpath("//ul[@id='breadcrumbs-one']/li[.//a][position()>2 and position()<=last()-1]//text()[string-length(normalize-space(.))>0]").join("|")
    if not category:
        category = data.xpath("//ul[@id='breadcrumbs-one']/li[.//a][position()>2]//text()[string-length(normalize-space(.))>0]").join("|")
    product.category = Category(name = category)
    product.ssid = re_search_once('\/([^\/]+)\.htm', product.url)

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath("//div[@class='artinfo']/span[@itemprop='datePublished']/text()[string-length(normalize-space(.))>0]").string()
    user = data.xpath("//div[@class='artinfo']/span[@itemprop='author']/text()[string-length(normalize-space(.))>0]").string()
    if user:
        review.authors.append(Person(name = user, ssid = user))
    excerpt = data.xpath("//div[@id='bodytext']/text()[string-length(normalize-space(.))>100][1]").string()
    if not excerpt:
        excerpt = data.xpath("//meta[@itemprop='description']/@content").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='excerpt'), value=excerpt))
    summary = data.xpath("//div[@id='bodytext']/h3[regexp:test(., 'Итог') or regexp:test(., 'Вывод')]/following-sibling::text()[string-length(normalize-space(.))>100][1]").string()
    if not summary:
        summary = data.xpath("//div[@id='nw12']/h3[regexp:test(., 'Итоги')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type=ReviewPropertyType(name='summary'), value=summary, name = "Итоги"))
	
    product.reviews.append(review)
    session.emit(product)