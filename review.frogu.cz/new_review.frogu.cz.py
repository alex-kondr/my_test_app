from agent import *
from models.products import *
import time
import random


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
    session.queue(Request('https://www.frogu.cz/', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//ul[@id="gridmax-menu-primary-navigation"]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//div[contains(@class, "gridmax-posts-grid")]/div')
    for rev in revs:
        title = rev.xpath('.//h3[contains(@class, "post-title")]/a/text()').string()
        url = rev.xpath('.//h3[contains(@class, "post-title")]/a/@href').string()
        ssid = rev.xpath('@id').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url, ssid=ssid))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['ssid'].replace('post-', '')
    product.category = context['cat']

    images = data.xpath('//div[@class="gridmax-box-inside"]//img')
    for img in images:
        img_alt = img.xpath('@alt').string()
        img_url = img.xpath('@src').string()
        if img_alt and img_url:
            product.add_property(type="image", value={'src': img_url, 'alt': img_alt})

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    grade_overall = data.xpath('//div[contains(text(), "vote)")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(contains(., "Affiliate program"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
