#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ['View all']


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
    r = agent.Request(url, proxies=['eu'])
    return r


def RequestRevs(pid, page):
    url = 'https://api.feefo.com/api-feefo/api/10/reviews/product?locale=en_GB&product_sku={pid}&origin=www.bootskitchenappliances.com&merchant_identifier=ao-retail-ltd&since_period=ALL&full_thread=include&unanswered_feedback=include&page={page}&page_size=5&sort=-updated_date&feefo_parameters=include&media=include&demographics=include&translate_attributes=exclude&empty_reviews=false'.format(pid=pid, page=page)
    r = Request(url)
    return r


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.bootskitchenappliances.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[not(@id)]/a[@class="top-level-menu-item"]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        cat_id = cat.xpath('@data-link').string()

        sub_cats = data.xpath('//div[contains(@data-link, "{}")]//ul[@class="sub-menu-3"]'.format(cat_id))
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('(.//a)[1]//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('(.//a)[position() > 1]')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                    url = sub_cat1.xpath('@href').string()

                    if sub_name1 not in XCAT:
                        session.queue(Request(url + '?pagesize=60'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('(.//a)[1]/@href').string()
                session.queue(Request(url + '?pagesize=60'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[contains(@class, "productInfoArea")]')
    for prod in prods:
        name = prod.xpath(".//h2//text()").string(multiple=True)
        ssid = prod.xpath('@productcolourid').string()
        mpn = prod.xpath('@productcode').string()
        brand = prod.xpath('.//a/@data-brand').string()
        url = prod.xpath(".//h2/a/@href").string()

        revs_cnt = prod.xpath('.//a[@class="gridPodReviews"]/text()').string()
        if revs_cnt and int(revs_cnt.replace('Reviews', '').strip('( )')) > 0:
            session.queue(RequestRevs(ssid, 1), process_reviews, dict(context, name=name, ssid=ssid, brand=brand, mpn=mpn, url=url))

    next_page = data.xpath('//link[@rel="next"]/@href').string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.ssid
    product.category = context['cat']

    if context['brand']:
        product.manufacturer = context['brand'].replace('brandSprite_', '').title()

    if context['mpn']:
        product.add_property(type='id.manufacturer', value=context['mpn'])

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.get('products', [{}])[0].get('id')

        date = rev.get('products', [{}])[0].get('created_at')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('customer', {}).get('display_name')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_ovevrall = rev.get('products', [{}])[0].get('rating', {}).get('rating')
        if grade_ovevrall:
            review.grades.append(Grade(type='overall', value=float(grade_ovevrall), best=5.0))

        is_verified_buyer = rev.get('products', [{}])[0].get('feedbackVerificationState')
        if is_verified_buyer and is_verified_buyer == 'merchantVerified':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('products', [{}])[0].get('helpful_votes')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        excerpt = rev.get('products', [{}])[0].get('review')
        if excerpt:
            excerpt = excerpt.strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    page_cnt = revs_json.get('summary', {}).get('meta', {}).get('pages', 0)
    next_page = revs_json.get('summary', {}).get('meta', {}).get('current_page', 1) + 1
    if page_cnt > next_page:
        session.queue(RequestRevs(context['ssid'], next_page), process_reviews, dict(context))
