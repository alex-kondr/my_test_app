from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.destructoid.com/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[h2 and contains(@class, "article-group__list")]//div[contains(@class, "article-tile__content")]//div[contains(@class, "article-tile__content-article-info-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review – ', '').split(' – ')[0].split(' Review: ')[0].replace(' review', '').replace('Review: ', '').replace('Preview: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '').replace('review-', '')
    product.category = 'Tech'

    platforms = data.xpath('(//p[@data-injectable and regexp:test(., ".+\(.*PC[^\(\)]+\)|.+\(.*PS[^\(\)]+\)|.+\(.*Xbox[^\(\)]+\)|.+\(.*Nintendo[^\(\)]+\)")]|//b[regexp:test(., ".+\(.*PC[^\(\)]+\)|.+\(.*PS[^\(\)]+\)|.+\(.*Xbox[^\(\)]+\)|.+\(.*Nintendo[^\(\)]+\)")])[not(regexp:test(., "review|tests|tested|to test"))]//text()').string(multiple=True)
    if platforms:
        product.category = 'Games|' + re.sub(r'[  ]?\[[^\[\]]*reviewe?d[^\[\]]*\]|[  ]?\[tested\]|\[Review\]', '', platforms, flags=re.I).replace('and ', '').split('(', 1)[-1].split(')')[0].replace(' [played the first hours before saying screw this/it’s Doom/bought a review code for…]', '').replace(' [reviewed with PlayStation VR', '').replace(' [tested on both regular Pro]', '').replace(' [reviewed with PSVR', '').replace(' [reviewed[', '').replace(' (reviewed', '').replace(' – rig', '').strip('( )').replace(', ', '/').replace(', ', '/').replace(' /', '/')

    manufacturer = data.xpath('(//b|//strong)[contains(., "Developer:")]/text()[contains(., "Developer:")]').string(multiple=True)
    if manufacturer:
        product.manufacturer = manufacturer.replace('Developer:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//p/@data-datetime').string()
    if date:
        date = re.search(r'\w{2,4} \d{1,2}, \d{4}', date)
        if date:
            review.date = date.group()

    author = data.xpath('//div[contains(@class, "author-drawer__author")][normalize-space(.)]/text()').string()
    author_ssid = data.xpath('//div[contains(@class, "author-drawer__author")][normalize-space(.)]/@data-author').string()
    if author and author_ssid:
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "summary__number-rating")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[div[contains(text(), "Pros")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div[contains(text(), "Cons")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "header__content--subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "article-content")]/p[not(regexp:test(., "Developer:|Publisher:|Released:|MSRP:") or sub)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()

        if 'Overall, ' in excerpt:
            excerpt, conclusion = excerpt.rsplit('Overall, ', 1)
            conclusion = conclusion.strip().capitalize()
            review.add_property(type='conclusion', value=conclusion)
        else:
            conclusion = data.xpath('//div[contains(@class, "review-summary__text")]/p//text()').string(multiple=True)
            if conclusion:
                review.add_property(type='conclusion', value=conclusion)

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
