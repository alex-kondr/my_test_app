from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.independentgolfreviews.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="menu-list"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        sub_cats = cat.xpath('ul[@class="sub-menu"]/li/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name+'|'+sub_name, cat_url=url))


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not re.search(r'Best |Top |Most |Longest ', title):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_page = data.xpath('//button[@class="data-caret" and @data-action="next"]')
    if next_page:
        next_page = context.get('page', 1) + 1
        next_url = context['cat_url'] + '?page_num=' + str(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Review', '').replace('REVIEW:', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//h2[contains(., "Buy")]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if not date:
        date = data.xpath('//time/@datetime').string()

    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="author-title"]//text()').string()
    author_url = data.xpath('//a[@class="author-title"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//p[.//strong[contains(., "Quick Hits")]]/text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    summary = data.xpath('//p[contains(@class, "has-text-color")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Summary")]/following-sibling::p[not(contains(., "For more information:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Summary")]/preceding-sibling::p[not(contains(@class, "has-text-color"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(contains(@class, "has-text-color") or regexp:test(., "For more information:|Quick Hits"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
