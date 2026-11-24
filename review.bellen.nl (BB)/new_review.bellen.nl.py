#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.bellen.com/sitemap.xml'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    urls = data.xpath('//*[local-name()="loc"][contains(text(), "/review")]/text()')
    for url in urls:
        url = url.string()
        if url and not session.seen(url):
            session.queue(Request(url, ignore_errors=True), process_product, dict(context, url=url))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    title = data.xpath('//h1//text()').string()
    if not title:
        return

    product = Product()
    product.name = title.split(' review')[0].split(' Review')[0].split(': ')[-1].replace('Toestelreview ', '').replace('Review ', '').replace('nieuwe ', '').strip()
    product.url = context['url']
    product.ssid = product.url.replace('https://www.bellen.com/', '').replace('/review', '').replace('/', '-').strip('-')
    product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//p[contains(., "Geactualiseerd:")]//text()').string()
    if date:
        date = date.split('Geactualiseerd:', 1)[-1].strip().split()[0]
        if date:
            review.date = date

    author = data.xpath('//div[contains(@id, "reviews")]//p[starts-with(normalize-space(.), "Door ")]/text()').string()
    if author and 'Door ' in author:
        author = author.split('Door ')[1].split(',')[0].strip()
        if author:
            review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//div[contains(@id, "reviews")]//h2[contains(., "Conclusie")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.split('Geactualiseerd')[0].strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@id, "reviews")]//h2[contains(., "Conclusie")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@id, "reviews")]//p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.split('Geactualiseerd')[0].strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
