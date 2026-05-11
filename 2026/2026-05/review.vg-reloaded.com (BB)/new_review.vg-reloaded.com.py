from agent import *
from models.products import *
import time


SLEEP = 2
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Alt-Used: www.vg-reloaded.com' -H 'Connection: keep-alive' -H 'Cookie: PHPSESSID=03d96bf0a8e9203530043af3aecb1b2b; cmplz_banner-status=dismissed' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.vg-reloaded.com/category/articles/', use='curl', options=OPTIONS, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    time.sleep(SLEEP)

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', options=OPTIONS, max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    time.sleep(SLEEP)

    product = Product()
    product.name = context['title'].split(': ', 1)[-1].replace('PC Review – ', '').replace('DS Review – ', '').replace('Preview – ', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//article[contains(@class, "type-post")]/@id').string().split('-')[-1]
    product.category = 'Games'

    if ' Review' in context['title']:
        platform = context['title'].split(' Review')[0].replace('X/S', 'X\\S').strip()
        if platform and 'review' not in platform.lower():
            product.category += '|' + platform

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.type = "pro"

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "meta-author")]/a/text()').string()
    author_url = data.xpath('//span[contains(@class, "meta-author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade = data.xpath('//h1[regexp:test(., "score:", "i")]//text()').string(multiple=True)
    if not grade:
        grade = data.xpath('//div[contains(@class, "entry-content")]/p[regexp:test(., "score:", "i")]/text()').string()
    if not grade:
        grade = data.xpath('//h1[regexp:test(normalize-space(text()), "^\d\.?\d?$")]/text()').string()

    if grade:
        grade = grade.split(':')[-1].split('/')[0].strip()
        if grade[0].isdigit():
            review.grades.append(Grade(type="overall", value=float(grade), best=10.0))

    summary = data.xpath('//div[contains(@class, "entry-content")]/p[1]/strong//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//div[contains(@class, "entry-content")]/p[preceding-sibling::p[regexp:test(., "the verdict", "i")]]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "the verdict", "i") or preceding::*[regexp:test(., "the verdict", "i")])]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        if len(excerpt) > 3:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

            session.emit(product)
