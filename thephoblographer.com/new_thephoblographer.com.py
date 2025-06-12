from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.thephoblographer.com/reviews/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul[contains(@class, "list")]/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()

        if 'The Best ' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review')[0].replace('Review: ', '').replace(' review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[contains(@href, "https://amzn.to")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "meta-author")]/a/text()').string()
    author_url = data.xpath('//div[contains(@class, "meta-author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('((//h3[regexp:test(normalize-space(text()), "Pros")]/following-sibling::*)[1]|(//h3[regexp:test(normalize-space(text()), "Likes")]/following-sibling::*)[1])/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('((//h3[regexp:test(normalize-space(text()), "^Cons")]/following-sibling::*)[1]|(//h3[regexp:test(normalize-space(text()), "Dislikes")]/following-sibling::*)[1])/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="has-drop-cap"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(preceding-sibling::h3[regexp:test(., "Pros|Cons")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]/p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
