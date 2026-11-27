#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XREV = ['best ', 'top ', 'sale', 'deal', ' vs. ']


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


def Request(url):
    r = agent.Request(url)
    r.add_header('Accept-Encoding', 'deflate')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.businessinsider.com/guides/tech'), process_frontpage, dict(cat='Tech'))


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[a[@data-analytics-product-area="tech"]]/ul/li/a[@class="hub-nav-dropdown-link "]')
    for cat in cats:
        url = cat.xpath('@href').string()
        name = cat.xpath('text()').string()
        session.queue(Request(url), process_revlist, dict(cat=context['cat'] + '|' + name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h3[@class="tout-title"]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        title = rev.xpath('text()').string()
        if not any(word in title.lower() for word in XREV) and not session.seen(url.split('/')[-1]):
            session.queue(Request(url), process_review, dict(context, url=url, title=title))

    # no next page


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('review:')[0].replace('Review', '').strip()
    product.category = context['cat']
    product.url = data.xpath('//a[@data-purchase-options-index]/@href').string() or context['url']

    product.ssid = data.xpath('//meta[@name="viking-id"]/@value').string()
    if not product.ssid:
        product.ssid = product.url.split('/')[-1].replace('-review', '')

    manufacturer = data.xpath('''//script[contains(., '"brand":"')]//text()''').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('"brand":"')[-1].split('"')[0]

    mpn = data.xpath('''//script[contains(., '"productId":"')]//text()''').string()
    if mpn:
        mpn = mpn.split('"productId":"')[-1].split('"')[0]
        product.add_property(type='id.manufacturer', value=mpn)


    review = Review()
    review.type = 'pro'
    review.url = context['url']
    review.ssid = product.ssid
    review.title = context['title']

    date = data.xpath('//time[contains(@class, "byline-timestamp headline-regular")]/@data-timestamp').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="byline-link byline-author-name"]//text()').string()
    author_url = data.xpath('//a[@class="byline-link byline-author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, profile_url=author_url, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    # no grades

    pros = data.xpath('//div[@class="pros-and-cons__subgrid-container"][strong[contains(., "we like")]]/ul/li/span/text()').strings()
    if not pros:
        pros = data.xpath('//aside[p[contains(., "What works")]]/following-sibling::ul[1]/li//text()').strings()

    if not pros:
        pros = data.xpath('//p[strong[text()="Pros"]]/text()').strings()
    for pro in pros:
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pros-and-cons__subgrid-container"][strong[contains(., "don’t like")]]/ul/li/span//text()').strings()
    if not cons:
        cons = data.xpath('//aside[p[contains(., "What needs work")]]/following-sibling::ul[1]/li//text()').strings()
    if not cons:
        cons = data.xpath('//p[strong[text()="Cons"]]/text()').strings()

    for con in cons:
        review.add_property(type='cons', value=con)


    summary = data.xpath('//ul[@class="summary-list"]/li//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[@id="the-bottom-line"]/following-sibling::p[not(strong[text()="Pros"])][not(strong[text()="Cons"])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(@id, "should-you-buy")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion and 'review: ' in review.title:
        conclusion = review.title.split('review: ')[-1]

    if conclusion:
        conclusion = conclusion.strip()
        review.add_property(type='conclusion', value=conclusion)


    excerpt = data.xpath('//div[@class="content-lock-content"]/p[not(contains(@class, "financial"))]//text()').string(multiple=True)
    if excerpt:

        if conclusion:
            excerpt = excerpt.split(conclusion)[0]

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
