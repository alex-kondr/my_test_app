from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.trailrunmag.com/category/shoe-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Shoe'))
    session.queue(Request('https://www.trailrunmag.com/category/gear-reviews/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Gear'))


def process_revlist(data, context, session):
    revs = data.xpath('//h3[@class="h3"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'Top \d+|Trail gear reviews', title):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('SHOE REVIEW:', '').replace('Shoe Review:', '').replace('Shoe Review –', '').replace('Gear preview:', '').replace('SHOE REVIEW - ', '').replace('Watch Preview: ', '').replace('We Tested: ', '').replace('Shoe review:', '').replace('Gear review:', '').replace('Trail shoe review:', '').replace('- early review', '').replace(' review 2024', '').replace('REVIEW:', '').replace('Review:', '').replace(' Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://www.trailrunmag.com/author/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.trailrunmag.com/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('(//h1[normalize-space(text())="Pros"]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h1[normalize-space(text())="Cons"]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "intro__text")]/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[.//b[contains(., "Verdict")]]/following-sibling::p[not(contains(., "Grab your copy here"))]//text()[not(regexp:test(., "^.+:|www."))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[.//b[contains(., "Verdict")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article__body")]/p[not(contains(., "Grab your copy here"))]//text()[not(regexp:test(., "^.+:|www."))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
