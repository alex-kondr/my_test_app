#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


X_MULTIPRODS = ['https://www.rockpapershotgun.com/best-amazon-prime-early-access-sale-deals', 'https://www.rockpapershotgun.com/amazon-prime-early-access-sale-2022-dates-and-what-to-expect', 'https://www.rockpapershotgun.com/how-to-clean-your-keyboard', 'https://www.rockpapershotgun.com/how-to-install-an-ssd', 'https://www.rockpapershotgun.com/intel-11th-gen-rocket-lake-cpu-release-date-specs-price', 'https://www.rockpapershotgun.com/heres-a-list-of-all-the-nvidia-g-sync-compatible-monitors-confirmed-so-far']
MULTIPRODS_URLS = ['https://www.rockpapershotgun.com/the-pc-hardware-with-the-most-unfitting-halloween-y-names']
MULTIPRODS_2 = ['https://www.rockpapershotgun.com/forza-horizon-4-graphics-performance-how-to-get-the-best-settings-on-pc', 'https://www.rockpapershotgun.com/metro-exodus-pc-graphics-performance-how-to-get-the-best-settings-2', 'https://www.rockpapershotgun.com/monster-hunter-world-pc-performance-best-settings-for-iceborne', 'https://www.rockpapershotgun.com/the-division-2-pc-performance-warlords-of-new-york', 'https://www.rockpapershotgun.com/cyberpunk-2077-ray-tracing-performance']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('http://www.rockpapershotgun.com/pc-game-reviews/'), process_revlist, dict(cat='Games|PC'))
    session.queue(Request('https://www.rockpapershotgun.com/category/hardware/'), process_revlist, dict(cat='Hardware'))
    run_vr(context, session)


def run_vr(context, session):
    session.queue(Request('https://www.rockpapershotgun.com/companies/meta'), process_revlist, dict(cat='VR'))
    session.queue(Request('https://www.rockpapershotgun.com/companies/facebook'), process_revlist, dict(cat='VR'))
    session.queue(Request('https://www.rockpapershotgun.com/topics/oculus'), process_revlist, dict(cat='VR'))
    session.queue(Request('https://www.rockpapershotgun.com/topics/vr'), process_revlist, dict(cat='VR'))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@data-type="article"]')
    for rev in revs:
        url = rev.xpath('.//div[@class="details"]//a/@href').string()
        date = rev.xpath('.//div[@class="metadata"]//time/@datetime').string()
        if url and date and 'review' in url:
            date = date.split('T')[0]
            session.queue(Request(url), process_review, dict(context, url=url, date=date))

    next_url = data.xpath('//div[@class="next"]/a[not(span/@title="Last page")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    name = data.xpath('//meta[@property="og:title"]/@content').string()
    if not name:
        name = data.xpath('//blockquote/h4//text()').string()
    if not name:
        name = data.xpath('//div[@class="article_body"]/div/strong//text()').string()
    if not name:
        name = data.xpath('//h1[@class="title"]//text()').string()

    multiprods = data.xpath('//h2[@id]')
    if not multiprods:
        multiprods = data.xpath('//h3[@id]')
    if multiprods and len(multiprods) > 1 and context['url'] not in X_MULTIPRODS and "deals" not in name or context['url'] in MULTIPRODS_URLS:
        process_reviews(data, context, session)
        return

    product = Product()

    product.name = name.split(' review')[0].split(' specs')[0].replace("'", "’").split('Wot I Think: ')[-1].split('Wot I Think - ')[-1].split('Verdict: ')[-1].split(' Review')[0].split("Wot I Think (So Far): ")[-1].split(" - Wot I Think")[0]
    product.ssid = context['url'].split('/')[-1].replace('-review', '').replace('wot-i-think-', "")
    product.category = context['cat']

    product.url = data.xpath('//strong[contains(text(), "Price:")]/parent::li/a[position() = last()]/@href').string()
    if not product.url:
        product.url = data.xpath('//strong[contains(text(), "From:")]/parent::li/a/@href').string()
    if not product.url:
        product.url = data.xpath('//strong[contains(text(), "From:")]/following-sibling::a/@href').string()
    if not product.url:
        product.url = data.xpath('//a[@rel="sponsored noopener"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(text(), "official site")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(text(), "Steam page")]/@hrefs').string()
    if not product.url or "deals" in product.name:
        product.url = context['url']

    product.url = product.url.lstrip("+").replace('steam://openurl/', '')

    product.manufacturer = data.xpath('//strong[contains(text(), "Publisher:")]/parent::li/text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//strong[contains(text(), "Publisher:")]/following-sibling::text()[1]').string()

    review = Review()
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = context['date']

    title = data.xpath('//h1[@class="title"]//text()').string()
    if title:
        review.title = title.replace("'", "’")

    author = data.xpath('//span[@class="name"]/a').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, url=author_url))

    summary_content = data.xpath('//div[@class="article_body_content"]/strong[1]//text()').string()
    summary = data.xpath('(//div[@class="article_body_content"]/strong/following-sibling::text())[1]').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="article_body_content"]/p[1]/em//text()').string(multiple=True)
    if summary and summary_content != "Developer:":
        summary = summary.replace("'", "’").replace(" . ", ". ").replace(" , ", ", ")
        review.add_property(type='summary', value=summary)


    excerpt = data.xpath('//div[@class="article_body_content"]//p[not(strong[contains(text(), "Developer:")])][not(strong[contains(text(), "Release:")])]//text()').string(multiple=True)
    if excerpt and excerpt != '':
        excerpt = excerpt.replace("'", "’").replace(" . ", ". ").replace(" , ", ", ")
        if summary:
            excerpt = excerpt.replace(summary, "")
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    prods = data.xpath('//h2[@id]')
    if not prods or len(prods) == 1:
        prods = data.xpath('//h3[@id][not(contains(text(), "Frequently asked questions"))]')
    if not prods:
        prods = data.xpath('//h2[not(contains(@class, "section"))]')
    if context['url'] == "https://www.rockpapershotgun.com/cyberpunk-2077-ray-tracing-performance":
        prods = data.xpath('(//h3)[position() > 3 and position() < 12]')

    for prod in prods:
        product = Product()

        product.name = prod.xpath('text()').string().split('Far Cry New Dawn: ')[-1]
        product.category = context['cat']
        product.ssid = product.name.lower().replace(' ', '-')
        product.url = prod.xpath('following-sibling::blockquote[1]//strong[contains(text(), "Price:")]/parent::li/a[position() = last()]/@href').string()

        if not product.url:
            product.url = context['url']

        product.url = product.url.lstrip("+")

        if not product.name and context['url'] == "https://www.rockpapershotgun.com/control-game-pc-performance-how-to-get-the-best-settings":
            continue

        review = Review()
        review.title = product.name
        review.type = 'pro'
        review.ssid = product.ssid
        review.url = context['url']
        review.date = context['date']

        author = data.xpath('//span[@class="name"]/a').first()
        if author:
            author_name = author.xpath('text()').string()
            author_url = author.xpath('@href').string()
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, url=author_url))

        pros = prod.xpath('(following-sibling::p/strong[contains(text(), "What we like:")])[1]/parent::p/text()').string(multiple=True)
        if pros:
            pros = pros.split(' ✔️ ')
            for pro in pros:
                pro = pro.strip().replace('✔️ ', '')
                review.add_property(type="pros", value=pro)

        summary = prod.xpath('following-sibling::*[1]/strong//text()').string()
        if summary:
            summary = summary.replace("'", "’").replace(" . ", ". ").replace(" , ", ", ")
            review.add_property(type='summary', value=summary)

        excerpt = ""
        excerpt_content = prod.xpath('following-sibling::p')
        for content in excerpt_content:
            if content.xpath('strong[contains(text(), "What we like:")]') or content.xpath('strong[contains(text(), "Read more in our")]'):
                break
            if content.xpath('.//text()').string():
                excerpt += content.xpath('.//text()').string(multiple=True)
                if content.xpath('following::*[1][contains(text(), "Read more in our")]') or content.xpath('following::*[1][@data-style="list"]') or content.xpath('following-sibling::*[1]/li') or content.xpath('following-sibling::*[2]/@id') or content.xpath('following-sibling::*[2]/self::h2'):
                    break
                if review.url in MULTIPRODS_2 and content.xpath('following-sibling::*[2]/img') or content.xpath('following-sibling::*[2]/a/img') or content.xpath('following-sibling::*[1]/self::hr'):
                    break

        if excerpt != "":
            excerpt = excerpt.replace("'", "’").replace(" . ", ". ").replace(" , ", ", ")
            if summary:
                excerpt = excerpt.replace(summary, "")
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
