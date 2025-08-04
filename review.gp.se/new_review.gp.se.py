from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.gp.se/n%C3%B6je/film'), process_revlist, dict(cat='Film'))
    session.queue(Request('http://www.gp.se/om/Film'), process_revlist, dict(cat='Film'))
    session.queue(Request('http://www.gp.se/om/Filmrecension'), process_revlist, dict(cat='Film'))

    session.queue(Request('http://www.gp.se/n%C3%B6je/spel'), process_revlist, dict(cat='Spel'))
    session.queue(Request('http://www.gp.se/om/Spel'), process_revlist, dict(cat='Spel'))
    session.queue(Request('http://www.gp.se/om/Spelrecension'), process_revlist, dict(cat='Spel'))


def process_revlist(data, context, session):
    revs = data.xpath('//div[div/h2]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, url=url))

    next_page = data.xpath('//button[contains(., "Nästa") and not(@disabled)]').string()
    if next_page:
        next_page = context.get('page', 1) + 1
        next_url = data.response_url.split('?')[0] + '?page={}'.format(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    title = data.xpath('//h1//text()').string(multiple=True)

    product = Product()
    product.name = title
    product.url = context['url']
    product.ssid = product.url.split('.')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@data-testid="article-byline_top"]/span/a[@role="link"]/text()').string()
    author_url = data.xpath('//div[@data-testid="article-byline_top"]/span/a[@role="link"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    # grade_overall = data.xpath('//text()').string()
    # if grade_overall:
    #     review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    # pros = data.xpath('/li')
    # for pro in pros:
    #     pro = pro.xpath('.//text()').string(multiple=True)
    #     if pro:
    #         pro = pro.strip(' +-*.:;•,–')
    #         if len(pro) > 1:
    #             review.add_property(type='pros', value=pro)

    # cons = data.xpath('/li')
    # for con in cons:
    #     con = con.xpath('.//text()').string(multiple=True)
    #     if con:
    #         con = con.strip(' +-*.:;•,–')
    #         if len(con) > 1:
    #             review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@data-testid="article-top_article-lead"]/span//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    # conclusion = data.xpath('//text()').string(multiple=True)
    # if conclusion:
    #     review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@data-testid="article-body_content"]/div/div/p//text()').string(multiple=True)
    # if not excerpt:
    #     excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
