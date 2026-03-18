from agent import *
from models.products import *
import HTMLParser
import time


SLEEP = 2
h = HTMLParser.HTMLParser()
XTITLE = [' Best ']


def serialize_text(text):
    text = h.unescape(text).replace('&#233;', 'é').replace('&#8232;', '').replace("", '').replace('', '').replace(' ', '').replace('', '').replace('', '').replace('', '').replace('﻿', '').replace('', '').replace('', '').replace('', '').replace('', '').replace('', ''). replace('', '').replace('', '').replace('', '').strip()
    return text


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.backpacker.com/gear-reviews/', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    time.sleep(SLEEP)

    revs = data.xpath('//article//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url, max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    time.sleep(SLEEP)

    product = Product()
    product.name = serialize_text(context['title'].split('Gear Review: ')[-1])
    product.ssid = data.xpath('//article/@data-uuid').string()
    product.category = 'Gear'

    product.url = data.xpath('//a[@class="tm-c-button"]/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//h3[*[contains(., "Brand:")]]/text()[normalize-space()]').string()
    if manufacturer:
        product.manufacturer = serialize_text(manufacturer).replace(' Reviews', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = serialize_text(context['title'])
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[contains(@class, "timestamp")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//a[@rel="author"]')
    for author in authors:
        author_name = serialize_text(author.xpath('strong/text()').string())
        author_url = author.xpath('@href').string()
        author_ssid = author_url.strip('/').split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    grade_overall = data.xpath('//div[contains(@class, "in-article")]/*[self::h1 or self::h2 or self::h3 or self::h4][preceding-sibling::*[self::h1 or self::h2 or self::h3 or self::h4][1][regexp:test(., "( Score| rating)", "i")]]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.strip())
        review.grades.append(Grade(name="Rating", value=grade_overall, best = 5.0, type='overall'))

    pros = data.xpath('//div[contains(@class, "in-article")]/p[regexp:test(., "^\s*pros\s*:", "i")]/text()').string()
    if pros:
        pros = serialize_text(pros).strip(' \n*-')
        if 'pros:' in pros.lower():
            pros = pros.split(': ')[-1].split(', ')
            for pro in pros:
                review.add_property(type='cons', value=pro.strip())
        elif pros:
            review.add_property(type='pros', value=pros)

    cons = data.xpath('//div[contains(@class, "in-article")]/p[regexp:test(., "^\s*cons\s*:", "i")]/text()').string()
    if cons:
        cons = serialize_text(cons).strip(' \n*-')
        if 'cons:' in cons.lower():
            cons = cons.split(': ')[-1].split(', ')
            for con in cons:
                review.add_property(type='cons', value=con.strip())
        elif cons:
            review.add_property(type='cons', value=cons)

    summary = data.xpath('//div[@class="c-article-dek"]/p//text()[normalize-space()]').string(multiple=True)
    if summary:
        summary = serialize_text(summary)
        if summary:
            review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "in-article")]/p[not(regexp:test(., "^\s*(\$\d*;|pros\s*:|cons\s*:)", "i"))][not(regexp:test(., "^\s*\*\s*Overall", "i"))][not(regexp:test(., "^\s*(Originally published|Published.*;)", "i"))]//text()[not(parent::*[regexp:test(., "^\s*(\$\d*;|pros\s*:|cons\s*:)", "i")])]').string(multiple=True)
    if excerpt:
        excerpt = serialize_text(excerpt)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)