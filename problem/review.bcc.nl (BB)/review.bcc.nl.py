#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *
import re, string

def run(context, session): 
    session.queue(Request('https://www.bcc.nl/'), process_frontpage, {})

def process_frontpage(data, context, session):
    for cat in data.xpath("//li[regexp:test(.,'Categorieën')]/following-sibling::li/a"):
        category = cat.xpath("descendant::text()").string(multiple=True)
        for sub in cat.xpath("following-sibling::div/ul/li[@class='header-mainnavigation-category-li']/a"):
            subcat = sub.xpath(".//text()").string(multiple=True)
            cat_url = sub.xpath("@href").string()
            if category and subcat and cat_url:
                context['category'] = category + '|' + subcat
                session.queue(Request(cat_url), process_productlist, context)

def process_productlist(data, context, session):
    cnt = 0
    for p in data.xpath("//div[regexp:test(@class, '^productlist')]/div[regexp:test(@id,'product-\d+')]"):
        cnt += 1
        context['name'] = p.xpath("descendant::h3/text()").string()
        context['url'] = p.xpath("descendant::a[@class='lister-product__titlelink']/@href").string()
        context['ssid'] = re_search_once('(\d+)$', p.xpath("@id").string())
        revs = p.xpath("descendant::span[@class='review__text']/text()").string()
        if context['name'] and context['url'] and revs:
            session.queue(Request(context['url']), process_product, context)

    next = data.xpath("//ul[@class='pagination']/li[regexp:test(normalize-space(.),'Volgende pagina')]/a/@href").string()
    if next and cnt > 15:
        session.queue(Request(next), process_productlist, context)

def process_product(data, context, session):
   prod = dict()
   prod['name'] = context['name']
   prod['url'] = context['url']
   prod['ssid'] = context['ssid']  
   prod['category'] = data.xpath("//ol[@class='breadcrumb breadcrumbs-show-all']/li/a/text()").join('|')
   prod['manufacturer'] = data.xpath("//th[regexp:test(.,'Merk')]/following-sibling::td/text()").string()
   prod['id.ean'] = data.xpath("//th[regexp:test(.,'EAN')]/following-sibling::td/text()").string()

   revs = data.xpath("//div[@class='rating__container']/span[@class='review__text']/text()").string()
   print 'revs --> ', revs
   if revs:
       pid = prod['ssid']
       passkey = "caiHyFuaMc47RFeOTCeTcXe5sSqF6VhVyRZNnilzz2SNo"
       locale = 'nl_NL'
       displaycode = "18862-nl_nl"

       process_reviews_request(data, dict(product=prod, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)
   