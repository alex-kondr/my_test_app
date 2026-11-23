#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    options = "-H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 11.1; rv:84.0) Gecko/20100101 Firefox/84.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8' -H 'Accept-Language: ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3' --compressed -H 'Connection: keep-alive' -H 'Referer: https://hwtech.ru/android' -H 'Upgrade-Insecure-Requests: 1' -H 'TE: Trailers'"
    r = agent.Request(url, use='curl', options='-s -L --insecure '+options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://hwtech.ru/android/page/1'), process_revlist, dict())
    # session.queue(Request('https://hwtech.ru/rival-stars-horse-racing-na-pk.html'), process_product, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath("//h2[@class='title front-view-title']/a")
    for rev in revs:
        name = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))
    
    next_url = data.xpath("//li/a[contains(.,'Далее')]/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-1].split('.html')[0]
    product.category = data.xpath("//li[contains(@class,'menu-item-object-category')]//text()").string()
    product.url = context['url']
    
    review = Review()
    review.title = context['name']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//meta[@property='article:published_time']/@content").string().split('T')[0]
    
    excerpt = data.xpath("//div[@itemprop='articleBody']//p//text()").string(multiple=True)
    
    summary = data.xpath("//meta[@property='og:description']/@content").string(multiple=True)
    if summary:
        if excerpt:
            excerpt = excerpt.replace(summary, '')
        review.properties.append(ReviewProperty(type='summary', value=summary))
    
    pros = data.xpath("//div[@itemprop='articleBody']//p[contains(.,'Плюсы:')]//following-sibling::ul/li")
    for pro in pros:
        pro = pro.xpath(".//text()").string().replace('+ ', '').strip()
        if pro:
            if excerpt:
                excerpt = excerpt.replace(pro, '')
            review.add_property(type='pros', value=pro)
    
    cons = data.xpath("//div[@itemprop='articleBody']//p[contains(.,'Минусы:')]//following-sibling::ul/li")
    for con in cons:
        con = con.xpath(".//text()").string().replace('- ', '').strip()
        if con:
            if excerpt:
                excerpt = excerpt.replace(con, '')
            review.add_property(type='cons', value=con)

    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
    
    product.reviews.append(review)
    session.emit(product)
