from agent import *
from models.products import *
import time
import random


OPTIONS = """curl 'https://pluggedingolf.com/category/reviews/fairwaywoods/' --compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Referer: https://pluggedingolf.com/' -H 'Cookie: ct_checkjs=277158b25d470642b40a35e629286e2b97386d97767df0b71258a1e48f326304; ct_ps_timestamp={time1}; ct_fkp_timestamp={time2}; ct_pointer_data=%5B%5B222%2C1308%2C707%5D%2C%5B286%2C1333%2C790%5D%2C%5B339%2C1402%2C1158%5D%2C%5B386%2C1696%2C1308%5D%2C%5B386%2C1698%2C2075%5D%2C%5B386%2C1700%2C2108%5D%2C%5B387%2C1706%2C2275%5D%2C%5B387%2C1708%2C3860%5D%2C%5B384%2C1713%2C4177%5D%2C%5B388%2C1714%2C4694%5D%2C%5B400%2C1743%2C4962%5D%2C%5B400%2C1740%2C5011%5D%2C%5B401%2C1741%2C5279%5D%2C%5B401%2C1741%2C5311%5D%2C%5B401%2C1743%2C5461%5D%2C%5B401%2C1745%2C5645%5D%2C%5B398%2C1740%2C5962%5D%2C%5B290%2C1130%2C6079%5D%2C%5B253%2C722%2C6229%5D%2C%5B239%2C591%2C6396%5D%2C%5B242%2C590%2C6897%5D%2C%5B520%2C1332%2C7014%5D%2C%5B569%2C1472%2C7163%5D%2C%5B505%2C1692%2C7314%5D%2C%5B507%2C1693%2C7848%5D%2C%5B375%2C572%2C12836%5D%2C%5B400%2C257%2C12920%5D%2C%5B421%2C206%2C13070%5D%2C%5B421%2C205%2C13387%5D%2C%5B421%2C198%2C13787%5D%2C%5B422%2C198%2C14137%5D%2C%5B426%2C200%2C14170%5D%2C%5B520%2C115%2C17008%5D%2C%5B311%2C414%2C17124%5D%2C%5B260%2C463%2C17292%5D%2C%5B228%2C546%2C17474%5D%2C%5B241%2C563%2C17608%5D%2C%5B242%2C565%2C17824%5D%2C%5B240%2C566%2C19059%5D%2C%5B286%2C580%2C19159%5D%2C%5B329%2C587%2C19309%5D%5D; ct_timezone=2; ct_screen_info=%7B%22fullWidth%22%3A1920%2C%22fullHeight%22%3A3195%2C%22visibleWidth%22%3A1920%2C%22visibleHeight%22%3A947%7D; apbct_headless=false; ct_checked_emails=0; ct_checked_emails_exist=0; ct_mouse_moved=true' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    # time1 = time.time()
    session.queue(Request('https://pluggedingolf.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())
    # session.queue(Request('https://pluggedingolf.com/', use='curl', force_charset='utf-8', options=OPTIONS.format(time1=time1, time2=time1+40)), process_frontpage, dict())


def process_frontpage(data, context, session):
    # time1 = time.time()

    cats = data.xpath('//li[a[contains(text(), "Reviews")]]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name + '|' + sub_name))
                # session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS.format(time1=time1, time2=time1+40)), process_revlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))
            # session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS.format(time1=time1, time2=time1+40)), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    # time1 = int(time.time())
    # time2 = time1 + random.randint(0, 50)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))
        # session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS.format(time1=time1, time2=time2)), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if not next_url and not context.get('restart1'):
        time.sleep(600)
        time1 = int(time.time())
        time2 = time1 + random.randint(0, 50)
        session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS.format(time1=time1, time2=time2)), process_revlist, dict(context, restart1=True))

    if next_url:
        time.sleep(10)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))
        # session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS.format(time1=time, time2=time1+40)), process_revlist, dict(context))


def process_review(data, context, session):
    if not data.xpath('//div[@class="elementor-widget-container" and h2]/p') and not context.get('restart'):
        time.sleep(600)
        time1 = int(time.time())
        time2 = time1 + random.randint(0, 50)
        session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS.format(time1=time1, time2=time2)), process_review, dict(context, restart=True))

    product = Product()
    product.name = context['title'].replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat'].replace(' Reviews', '').strip()

    product.url = data.xpath('//h2[regexp:test(., "Buy.here|Shop.HERE", "i")]/a/@href').string()
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

    author = data.xpath('//div[section[@itemprop="author"]]//div[@itemprop="name"]//text()').string()
    author_url = data.xpath('//div[section[@itemprop="author"]]//div[@itemprop="name"]/a/@href').string()
    if author and author_url and author_url.split('/')[-2]:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="elementor-widget-container" and h2]/p//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)

    time.sleep(10)
