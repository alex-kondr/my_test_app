import string
from agent import *
from models.products import *
import re

def process_view_category(data, context, session):
    for view_categoryline in data.xpath("//h2[@class='serif']//a"):
        context['product_url'] = view_categoryline.xpath("@href").string()
        context['product_name'] = view_categoryline.xpath("text()[string-length(normalize-space(.))>1]").string()
        context['date'] = view_categoryline.xpath("following::span[@class='date'][1]/text()[string-length(normalize-space(.))>1]").string()
        if context['date'] and context['product_url'] and context['product_name']:
            session.queue(Request(context['product_url']), process_product, context)
    next = data.xpath("//link[@rel='next']/@href").string()
    if next:
        session.queue(Request(next), process_view_category, context)

def process_product(data, context, session): 
    product = Product()
    product.url = context['product_url'] 
    product.ssid = context['product_url']
    product.name = context['product_name']
    product.category = data.xpath("//img[contains(@data-src,'folder_stroke_12x12.png')]/following-sibling::a/text()[string-length(normalize-space(.))>1]").join(", ")

    for imageline in data.xpath("//meta[@property='og:image']"):
        url_image = imageline.xpath("@content").string()
        if url_image:
            product.properties.append(ProductProperty(type='image' , value = {'src': url_image, 'type': 'product'}))

    review = Review()
    review.url = context['product_url'] 
    review.ssid = context['product_url'] 
    review.title = context['product_name']
    review.type = 'pro'
    review.date = re_search_once('(\d+.+)', context['date'])

    username1 = data.xpath("//div[@class='auteur_art']/text()[string-length(normalize-space(.))>1][regexp:test(.,'Par ')]").string()
    if username1:
        username = re_search_once('Par (.+)\|', username1)
        review.authors = Person(name = username, ssid = username)

    excerpt = data.xpath("//meta[@name='description']/@content").string()
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value = excerpt))

    summary = data.xpath("//p/b[text()[regexp:test(.,'conclu')]]//text()[string-length(normalize-space(.))>1]").join(" ")
    if summary:
        review.properties.append(ReviewProperty(name='Conclure', type='summary', value=summary))      

    product.reviews.append(review)

    if product.category:
      session.emit(product)

def run(context, session):
    session.queue(Request('https://www.qobuz.com/fr-fr/info/-MAGAZINE-ACTUALITES/HI-FI-BANCS-D-ESSAI298'), process_view_category, {}) 