from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://cybershack.com.au/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[contains(@class, "next ")]/@href').string()

    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' – ')[0].split(': ')[0].replace('(review)', '').strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(@href, "www.amazon.com.") or contains(text(), "Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[contains(@class, "post__category")]/a[not(contains(., "Review"))]/text()').join('|')
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://cybershack.com.au/author/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://cybershack.com.au/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

# https://cybershack.com.au/reviews/google-pixel-watch-3-the-heartbeat-is-strong-wearable-review/
    overall = data.xpath('//h3[regexp:test(text(), " rating", "i")]/following-sibling::p[not(preceding-sibling::p[strong[contains(text(), "Pro") or contains(text(), "Con")]] or strong[contains(text(), "Pro")])]//text()').string(multiple=True)
    if overall:
        grade_overall = re.search(r'\d+\.?\d?/\d+', overall)
        if grade_overall:
            grade_overall, grade_best = grade_overall.group(0).split('/')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(grade_best)))

    pros = data.xpath('//p[strong[contains(., "Pro")]]/following-sibling::p[preceding-sibling::p[strong][1][strong[contains(., "Pro")]]][not(strong)]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[strong[contains(., "Con")]]/following-sibling::p[preceding-sibling::p[strong][1][strong[contains(., "Con")]]][not(strong or @class or normalize-space(text())="None")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[regexp:test(text(), " rating", "i")]/following-sibling::p[not(preceding-sibling::p[strong[contains(text(), "Pro") or contains(text(), "Con")]] or strong[contains(text(), "Pro")])]//text()').string(multiple=True)
    if conclusion:
        conclusion = re.sub(r'\d+\.?\d?/\d+', '', conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[regexp:test(text(), " rating", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(@class or preceding-sibling::p[strong[contains(text(), "Pro") or contains(text(), "Con")]] or strong[contains(text(), "Pro")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
