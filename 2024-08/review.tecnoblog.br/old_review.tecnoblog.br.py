#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def run(context, session):
   session.queue(Request('https://tecnoblog.net/editoria/review/', use="curl"), process_revlist,  dict(next=''))
   #session.queue(Request('https://tecnoblog.net/categoria/review/', use="curl"), process_revlist, dict(next=''))


def strip_namespace(data):
   tmp = data.content_file + ".tmp"
   out = file(tmp, "w")
   for line in file(data.content_file):
       line = line.replace(' xmlns=', ' abcd=')
       line = line.replace('ns0:', '')
       out.write(line + "\n")
   out.close()
   os.rename(tmp, data.content_file)


def process_revlist(data, context, session):
    try:
        for rev in data.xpath('//div[@class="texts"]//node()[regexp:test(name(),"h\d")]//a'):
            url = rev.xpath('@href').string()
            title = rev.xpath('descendant::text()').string(multiple=True)
            if url and title:
                session.queue(Request(url, use="curl"), process_review, dict(url=url, title=title))

        nexturl = data.xpath('//a[@id="mais"]//@href').string()
        if nexturl:
            session.browser.use_new_parser = False
            session.queue(Request(nexturl, use="curl"), process_revlist, dict(next=nexturl))
    except:
        session.browser.use_new_parser = True
        session.do(Request(context['next'], use="curl"), process_revlist, dict(context))


def process_review(data, context, session):
    try:
        product = Product()

        product.name = re_search_once("^Review: (.*)$", context['title'])
        if not(product.name): product.name = context['title']

        product.url = context['url']
        product.ssid = re_search_once('postid-(\d+)', data.xpath('//body[contains(@class,"postid-")]/@class').string()) or product.url

        product.category = data.xpath('//a[@rel="tag"]//text()|//span[@id="breadcrumbs"]//a[text()!="Início"]//text()').join('|')
        if not(product.category): product.category = 'unknown'

        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.url = context['url']
        review.ssid = product.ssid

        pub_date = data.xpath('//div[@class="by"]//time//@datetime').string()
        if pub_date:
            if 'T' in pub_date: pub_date = pub_date.split('T')[0]
            review.date = pub_date
        else:
            review.date='unknown'

        author = data.xpath('//a[@rel="author"]').first()
        if author:
            name = author.xpath("descendant::text()").string()
            url = author.xpath("@href").string()
            if url and name:
                review.authors.append(Person(name=name, ssid=name, profile_url=url))

        overall = data.xpath('//div[@id="nota"]//span[not(@class)]//text()').string()
        if overall:
            review.grades.append(Grade(name='Overall Rating', type='overall', value=overall, best=10))

        for g in data.xpath('//div[@class="atr-nota"]'):
            name = g.xpath('div[1]//text()').string()
            value = g.xpath('div[2]//text()').string()
            if value and name:
                review.grades.append(Grade(name=name, value=value, best=10))

        excerpt = data.xpath('//meta[@property="og:description"]//@content').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

        conclusion = data.xpath('//node()[regexp:test(name(),"h\d")][regexp:test(descendant::text(),"(onclusão|ale a pena|txt3)")]/following-sibling::p//text()').string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        for pro in data.xpath('//node()[regexp:test(name(),"h\d")][contains(descendant::text(),"Prós")]/following-sibling::ul[1]//li'):
            line = pro.xpath("descendant::text()").string()
            if line:
                review.add_property(type='pros', value=line)

        for con in data.xpath('//node()[regexp:test(name(),"h\d")][contains(descendant::text(),"Contras")]/following-sibling::ul[1]//li'):
            line = con.xpath("descendant::text()").string()
            if line:
                review.add_property(type='cons', value=line)

        product.reviews.append(review)

        if product.reviews:
            session.emit(product)
            session.browser.use_new_parser = False
    except:
        session.browser.use_new_parser = True
        session.do(Request(context['url'], use="curl"), process_review, dict(context))
