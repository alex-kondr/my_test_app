#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import yaml

debug = True

def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=20000)]
    session.queue(Request('http://canaltech.com.br/analise/', use="curl"), process_category, dict(context))

    #url = 'https://www.googleapis.com/customsearch/v1element?key=AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY&rsz=filtered_cse&num=10&hl=pt_PT&prettyPrint=false&source=gcsc&gss=.br&sig=ddc80d38c7e2cb7b462cb57d9710fb58&cx=004659546419109346008:o_5stijrvfi&q=analise&cse_tok=AF14hlh4QGbKqx5yRV1NdvmMUT-U5CIPDA:1535125431781&start=0'
    #session.queue(Request(url, use="curl"), process_categoryJSON, dict(context, baseurl=url, start=0))

def process_categoryJSON(data, context, session):
    jstxt = data.content
    revs = yaml.load(jstxt)

    cnt = 0
    for rev in revs['results']:
        name=rev['titleNoFormatting']
        url=rev['url']

        bad_list = [', o ',', um ',' - V']
        for item in bad_list:
            if item in name:
                namex = name.split(item)[0]
                if len(namex) == 0:
                    name = name.split(item)[1]
                else:
                    name = namex
                break

        bad_list2 = ['Análise: ',' [Análise / Review]','[Comparativo]','[Análise]','[Unboxing]',
        '[Crítica]','[Hands-on]','Hands-on:','Comparativo:','Análise |','Análise']
        for item in bad_list2:
             if item in name:
                name = name.replace(item, '')

        session.queue(Request(url, use="curl"), process_review, dict(url=url, name=name))
        cnt +=1

    if cnt == 10:
        start = context['start'] + 10
        uri = context['baseurl'].replace('start=0','start='+str(start))
        session.queue(Request(uri, use="curl"), process_categoryJSON, dict(context, start=start))

def process_category(data, context, session):
    for link in data.xpath('//div[@class="row"]//article'):
        name = link.xpath('following-sibling::node()[regexp:test(name(),"h\d")][1]//text()').string(multiple=True)
        url = link.xpath('following-sibling::a[1]//@href').string(multiple=True)
        if url and name:
            bad_list = [', o ',', um ']
            for item in bad_list:
                if item in name:
                    namex = name.split(item)[0]
                    if len(namex) == 0:
                        name = name.split(item)[1]
                    else:
                        name = namex
                    break

            bad_list2 = ['Análise: ',' [Análise / Review]','[Comparativo]','[Análise]','[Unboxing]',
            '[Crítica]','[Hands-on]','Hands-on:','Comparativo:']
            for item in bad_list2:
                 if item in name:
                    name = name.replace(item, '')

            session.queue(Request(url, use="curl"), process_review, dict(url=url, name=name))

    next = data.xpath('//div[@id="loadMore"]//@data-page').string()
    if next:
        uri = 'https://canaltech.com.br/analises/p'+next+'/'
        session.queue(Request(uri, use="curl"), process_category, dict(context))

def process_review(data, context, session):
    product = Product()
    product.name = context['name']

    is_review = True
    # Category
    category = data.xpath('//ul[@class="breadcrumb"]/li[position()>1]//text()[string-length(normalize-space(.))>1]').join(' | ')
    if category:
        product.category = category
        if '|' not in category:
            if 'Mercado' in category: is_review = False
            if 'Internet' in category: is_review = False
            if 'Software' in category: is_review = False
    else:
        product.category = 'unknown'

    product.url = context['url']
    product.ssid = product.name + product.url

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid + ' review'

    # Publish date
    pub_date=data.xpath('//meta[@property="article:published_time"]//@content').string()
    if pub_date:
        if 'T' in pub_date: pub_date=pub_date.split('T')[0]
        review.date=pub_date
    else:
        review.date='unknown'

    # Author
    author=data.xpath('//span[@class="meta-info"]//a//text()').string(multiple=True)
    if author:
        review.authors.append(Person(name=author, ssid=author))
    else:
        review.authors.append(Person(name='canaltech.com.br', ssid='canaltech.com.br'))

    # Summary
    summary=data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(VALE A PENA|Conclus|Vale a pena)")]/following-sibling::p[string-length(normalize-space(.))>100]//text()').string(multiple=True)
    if summary:
        is_review = True
        review.properties.append(ReviewProperty(type='summary',value=summary))

    # Excerpt
    excerpt=data.xpath('//div[@class="content"]//p[string-length(normalize-space(.))>100]//text()').string(multiple=True)
    if excerpt:
        if summary: excerpt = ''.join(excerpt.split(summary))
        review.properties.append(ReviewProperty(type='excerpt',value=excerpt[:1111]))

    # Pros
    for p in data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Vantagens)")]/following-sibling::ul[1]//li'):
        pros=p.xpath('descendant::text()').string(multiple=True)
        if pros:
            is_review = True
            review.properties.append(ReviewProperty(type='pros',value=pros))

    # Cons
    for c in data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(Desvantagens)")]/following-sibling::ul[1]//li'):
        cons=c.xpath('descendant::text()').string(multiple=True)
        if cons:
            is_review = True
        review.properties.append(ReviewProperty(type='cons',value=cons))

    if is_review:
        product.reviews.append(review)

    if product.reviews:
        session.emit(product)
