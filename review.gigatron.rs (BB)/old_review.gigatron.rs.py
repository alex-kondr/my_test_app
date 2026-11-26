#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://gigatron.rs/', use='curl'), process_frontpage, {})


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    for cat in data.xpath("//div[@class='content']//ul[@class='items']//li[contains(@id, 'main-nav-')]/a"):
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, use='curl'), process_category, dict(category=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    for cat in data.xpath("//div[contains(@class, 'itemWrapperPC')]//div[@class='innerIWPC']//div[@class='catmenu-main']//h2//a"):
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        if url:
            split_data = url.split('/')[-1]
            if '?' == split_data[0]:
                url = 'https://search.gigatron.rs/v1/search/get' + split_data + '?poredak=rejting&strana=1'
            else:
                url = 'https://search.gigatron.rs/v1/catalog/get/' + split_data + '?poredak=rejting&strana=1'
            session.queue(Request(url, use='curl'), process_category_json, dict(category=name, page=1, url=url, t=0))


def process_category_json(data: Response, context: dict[str, str], session: Session):
    jsontxt = data.content
    if '},"hits"' in jsontxt:
        jsontxt = '{"hits"' + jsontxt.split('},"hits"')[-1]

    json = simplejson.loads(jsontxt)

    cnt = 0
    for prod in json['hits']['hits']:
        prod_data = prod['_source']['search_result_data']

        cnt += 1
        manufacturer = prod_data['brand']
        ssid = prod_data['product_id']
        sku = prod_data['id']
        ean = prod_data['ean']
        name = prod_data['name']
        url = 'https://gigatron.rs' + prod_data['url']

        session.queue(Request(url, use='curl'), process_product, dict(context, manufacturer=manufacturer, ssid=ssid, sku=sku, ean=ean, name=name, url=url))
        
    if cnt >= 24:
        context['page'] += 1
        context['url'] = context['url'].split('strana')[0] + 'strana=' + str(context['page'])
        session.queue(Request(context['url'], use='curl'), process_category_json, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['category']
    product.manufacturer = context['manufacturer']
    product.sku = str(context['sku'])
    product.ssid = str(context['ssid'])
    
    product.properties.append(ProductProperty(type='id.ean', value=str(context['ean'])))

    info = data.xpath("//script[contains(.,'window.__PRELOADED_STATE__')]//text()").string()
    if not info:
        return
    info = info.replace("window.__PRELOADED_STATE__ = ", "")
    info = simplejson.loads(info)

    revs = info['product']['average']['reviews']
    for rev in revs:
        review = Review()
        review.title = rev['title']
        review.type = 'user'
        review.url = product.url
        review.date = rev['date']
        review.ssid = rev['review_id']
        
        author_name = rev['first_name']
        review.authors.append(Person(name=author_name, ssid=author_name))
        
        grade_overall = rev['overall_new']
        if grade_overall:
            grade_overall = grade_overall.replace(',', '.').replace('width:', '').replace('%;', '')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        
        pros = rev['plus']
        if pros:
            review.add_property(type='pros', value=pros)
        
        cons = rev['minus']
        if cons:
            review.add_property(type='cons', value=cons)

        if pros or cons:
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
