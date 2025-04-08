from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.gameblog.fr/api/posts/load_more_posts/route/list_page/controller/components_controller/method/search_post_items/view_mode/full/sort_order/desc/offset/0/ppp/10/release_filter/a-venir/search_filters/Tech%2CHardware%20Tests%2Call%2Call%2C%2C%2C%2C%2C%2C%2C%2C%2C/limit/gameblog', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="item-content-header"]')
    for rev in revs:
        title = rev.xpath('h2[@class="title"]/text()').string()
        url = rev.xpath('a[contains(@class, "title")]/@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="name"]/text()').string()
    author_url = data.xpath('//a[@class="name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('0').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('0')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('0')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@itemprop="description about"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Végszó|Fnatic")]/following-sibling::p[@class="mgt0" or @class="mgt1"][not(s)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Végszó|Fnatic")]/preceding-sibling::p[@class="mgt0" or @class="mgt1"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-body")]/p[@class="mgt0" or @class="mgt1"]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
