from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://pluggedingolf.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[a[contains(text(), "Reviews")]]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//h2[regexp:test(., "Buy here", "i")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    # grade_overall = data.xpath('//text()').string()
    # if grade_overall:
    #     review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    # pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    # for pro in pros:
    #     pro = pro.xpath('.//text()').string(multiple=True)
    #     if pro:
    #         pro = pro.strip(' +-*.:;•,–')
    #         if len(pro) > 1:
    #             review.add_property(type='pros', value=pro)

    # cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    # for con in cons:
    #     con = con.xpath('.//text()').string(multiple=True)
    #     if con:
    #         con = con.strip(' +-*.:;•,–')
    #         if len(con) > 1:
    #             review.add_property(type='cons', value=con)

    # summary = data.xpath('//text()').string(multiple=True)
    # if summary:
    #     review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="elementor-widget-container" and h2]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
