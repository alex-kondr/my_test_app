#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def Request(url):
    r = agent.Request(url, proxies='rotating-eu', force_charset='utf-8')
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.mimundogadget.com/search?max-results=20'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[contains(@class, "entery-category")]')
    for rev in revs:
        title = rev.xpath('.//h2[contains(@class, "entry-title")]/a/text()').string()
        cat = rev.xpath('.//span[@class="post-tag"]/text()').string()
        url = rev.xpath('.//h2[contains(@class, "entry-title")]/a/@href').string()

        if url and title and not session.seen(url):
            session.queue(Request(url), process_review, dict(title=title, cat=cat, url=url))

    next_url = data.xpath('//a[contains(@class, "load-more")]/@data-load').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = context['cat'].title()

    product.name = data.xpath('//tr[contains(td/b, "Marca/Modelo")]/td[not(b)]/text()').string()
    if not product.name:
        product.name = context['title'].replace(u'‎', '').replace('[Review]', '').replace('[Análisis]', '').replace("[Reseña]", "").replace("[con vídeo]", "").strip().split(": ")[0].split("] ")[-1]

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'‎', '')
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="post-date published"]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    pros = data.xpath('//div[contains(div/text(), "Ventajas")]//ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(div/text(), "Inconvenientes")]//ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Conclusión")]/following::div[1]/div[not(preceding-sibling::div[@id] or @id)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusión")]/following-sibling::text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusión")]/following-sibling::div[not(@id)]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@id="postBody"]/div/div[not(@class or ul or preceding::h2[contains(., "Conclusión")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[@id="postBody"]/text()|(//div[@id="postBody"]/b|//div[@id="postBody"]/a)//text())[not(preceding::h2[contains(., "Conclusión")])]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
