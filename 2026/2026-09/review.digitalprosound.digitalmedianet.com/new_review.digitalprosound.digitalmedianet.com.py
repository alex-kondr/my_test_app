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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://digitalmedianet.com/category/audio/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//article[contains(@id, "post-")]')
    for rev in revs:
        title = rev.xpath('.//h3[contains(@class, "title")]/a//text()').string(multiple=True).replace('﻿', '').strip().strip()
        url = rev.xpath('.//h3[contains(@class, "title")]/a/@href').string()
        ssid = rev.xpath('@id').string().split('post-')[-1]
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url, ssid=ssid))

    next_url = data.xpath('//div/a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = "Audio"

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    # Not correct format of the date
    # review.date = data.xpath('//span[contains(@class, "posts-date")]/text()').string()

    date = data.xpath('//div[@class="entry-content"]/p//text()').strings()
    if date:
        date = ''.join(date)
        date = re_search_once(r"(\w+ \d{1,2}( ?th|st)?,? \d{4})", date)
        if date:
            review.date = date[0].capitalize()

    authors = data.xpath('//span[contains(@class, "posts-author")]/a')
    for author in authors:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.strip('/').split('/')[-1]

        if 'Staff' not in author_name:
            review.authors.append(Person(name=author_name, ssid=author_ssid))

    summary = data.xpath('//div[@class="post-excerpt"]/p//text()').string(multiple=True)
    if summary:
        summary = summary.replace('﻿', '').strip()
        if summary:
            review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="entry-content"]//p[not(regexp:test(., "for more information|please visit:", "i"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('﻿', '').strip()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt.strip())

            product.reviews.append(review)

            session.emit(product)