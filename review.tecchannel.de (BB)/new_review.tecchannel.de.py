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
    session.queue(Request('https://www.tecchannel.de'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ol[@class="TopicsList"]/li/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "article") and normalize-space(.//span[@class="card__content-type"])="Analyse"]')
    for rev in revs:
        title = rev.xpath('.//h3/text()').string()
        date = rev.xpath('.//div[contains(@class, "card__info card__info")]/span/text()[regexp:test(normalize-space(.), "^\d.+\d$")]').string()
        url = rev.xpath('@href').string()

        if not session.seen(url):
            session.queue(Request(url), process_review, dict(context, title=title, date=date, url=url))

    # no next page


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' im Test: ')[0].replace('Test:', '').replace('im Test', '').replace('Hands-On:', '')
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    authors = data.xpath('//div[@class="author__name"]/a')
    for author in authors:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    summary = data.xpath('//h2[@class="content-subheadline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="article-column__content"]/p[not(preceding::h2[contains(., "Fazit")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
