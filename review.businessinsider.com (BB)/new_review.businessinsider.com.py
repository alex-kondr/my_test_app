#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import urllib


XREVS = ['best ', 'top ', 'sale', 'deal', ' vs. ', ' vs ', 'compared']


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


def RequestRevs(feed_id, token=''):
    url = 'https://www.businessinsider.com/ajax/content-api/category/{feed_id}?templateId=tout-feed&capiVer=2&filter=tags%3Dcategory%3A{feed_id}%26tags%21%3Dtype%3Aredirect%26tags%3Dvertical%3Ainsiderpicks-electronics&size=20&page[limit]=20'.format(feed_id=feed_id)
    if token:
        url += '&nextPageToken=' + token
    r = agent.Request(url)
    r.add_header('Accept-Encoding', 'deflate')
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.businessinsider.com/guides/tech'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="link-block-links"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name and url:
            feed_id = url.rstrip('/').split('/')[-1]
            if feed_id == 'tvs':
                feed_id = 'tv'

            session.queue(RequestRevs(feed_id), process_revlist, dict(cat=name, feed_id=feed_id))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    try:
        revs_json = simplejson.loads(data.content).get(context['feed_id'], {})
    except:
        revs_json = {}

    new_data = revs_json.get('rendered')
    if new_data:
        new_data = data.parse_fragment(new_data)
        revs = new_data.xpath('//h3[contains(@class, "tout-title")]/a')
        for rev in revs:
            title = rev.xpath('text()').string()
            url = rev.xpath('@href').string()

            if title and url and '/guides/tech/' in url and not url.endswith('-awards') and not any(word in title.lower() for word in XREVS) and not session.seen(url):
                if url.startswith('/'):
                    url = 'https://www.businessinsider.com' + url

                session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_data = revs_json.get('links', {}).get('next')
    if next_data and 'nextPageToken=' in next_data:
        token = next_data.split('nextPageToken=')[-1].split('&')[0]
        session.queue(RequestRevs(context['feed_id'], token), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('review:')[0].replace('Review', '').strip()
    product.category = context['cat']

    product.url = data.xpath('//a[@data-purchase-options-index]/@href').string()
    if product.url and '&u=' in product.url:
        product.url = urllib.unquote(product.url.split('&u=')[-1].split('&')[0])
    else:
        product.url = context['url']

    product.ssid = data.xpath('//meta[@name="viking-id"]/@value').string()
    if not product.ssid:
        product.ssid = context['url'].rstrip('/').split('/')[-1].replace('-review', '')

    manufacturer = data.xpath('''//script[contains(., '"brand":"')]//text()''').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('"brand":"')[-1].split('"')[0]

    mpn = data.xpath('''//script[contains(., '"productId":"')]//text()''').string()
    if mpn:
        mpn = mpn.split('"productId":"')[-1].split('"')[0]
        product.add_property(type='id.manufacturer', value=mpn)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@data-timestamp').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//a[contains(@class, "byline-author-name")]')
    for author in authors:
        author_name = author.xpath('.//text()').string(multiple=True)
        author_url = author.xpath('@href').string()
        if author_name and author_url:
            author_ssid = author_url.rstrip('/').split('/')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    pros = data.xpath('//div[contains(@class, "pros-and-cons__section--pros")]//div[contains(@class, "pros-and-cons__item")]')
    for pro in pros:
        pro = pro.xpath('.//text()[not(ancestor::*[local-name()="svg"])]').string(multiple=True)
        if pro:
            pro = pro.strip(u' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "pros-and-cons__section--cons")]//div[contains(@class, "pros-and-cons__item")]')
    for con in cons:
        con = con.xpath('.//text()[not(ancestor::*[local-name()="svg"])]').string(multiple=True)
        if con:
            con = con.strip(u' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Should you buy") or contains(., "The bottom line")]/following-sibling::p[not(contains(@class, "financial"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Should you buy") or contains(., "The bottom line")]/preceding-sibling::p[not(contains(@class, "financial"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[contains(@class, "post-body-content")]/p[not(contains(@class, "financial"))]//text()').string(multiple=True)

    if excerpt and len(excerpt) > 2:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
