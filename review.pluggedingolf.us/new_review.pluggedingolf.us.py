from agent import *
from models.products import *
import time
import random


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Referer: https://pluggedingolf.com/category/reviews/putters/' -H 'Connection: keep-alive' -H 'Cookie: ct_sfw_pass_key=06d804612d17ab6fd6b8b2ff0c4e1c250; ct_checkjs=277158b25d470642b40a35e629286e2b97386d97767df0b71258a1e48f326304; ct_ps_timestamp={time1}; ct_fkp_timestamp={time2}; ct_pointer_data=%5B%5B105%2C1026%2C87%5D%2C%5B250%2C1339%2C289%5D%2C%5B136%2C1478%2C469%5D%2C%5B91%2C1518%2C594%5D%2C%5B46%2C1507%2C827%5D%2C%5B74%2C1528%2C14910%5D%2C%5B114%2C1607%2C14959%5D%2C%5B114%2C1605%2C15326%5D%2C%5B116%2C1604%2C15610%5D%2C%5B135%2C1600%2C15860%5D%2C%5B128%2C1580%2C15910%5D%2C%5B119%2C1576%2C16093%5D%2C%5B15%2C651%2C36931%5D%2C%5B120%2C715%2C37232%5D%2C%5B204%2C808%2C37365%5D%2C%5B453%2C1553%2C37515%5D%2C%5B580%2C1795%2C37682%5D%2C%5B517%2C1832%2C37832%5D%2C%5B447%2C1849%2C37982%5D%2C%5B442%2C1891%2C38149%5D%2C%5B442%2C1907%2C38299%5D%2C%5B442%2C1916%2C38533%5D%2C%5B97%2C1897%2C39151%5D%2C%5B123%2C1572%2C39218%5D%2C%5B251%2C697%2C39367%5D%2C%5B510%2C940%2C39517%5D%2C%5B488%2C997%2C39668%5D%2C%5B486%2C1008%2C39835%5D%2C%5B487%2C1009%2C39998%5D%2C%5B731%2C996%2C41453%5D%2C%5B684%2C716%2C41503%5D%2C%5B719%2C427%2C41636%5D%2C%5B737%2C338%2C41786%5D%2C%5B612%2C386%2C44473%5D%2C%5B433%2C475%2C44556%5D%2C%5B354%2C626%2C44940%5D%2C%5B348%2C621%2C45023%5D%2C%5B285%2C545%2C45174%5D%2C%5B250%2C491%2C45323%5D%2C%5B244%2C534%2C45474%5D%2C%5B235%2C562%2C45690%5D%2C%5B242%2C570%2C46791%5D%2C%5B385%2C590%2C46877%5D%2C%5B531%2C608%2C47026%5D%2C%5B538%2C609%2C47175%5D%2C%5B551%2C603%2C47376%5D%2C%5B552%2C603%2C47525%5D%5D; ct_timezone=2; ct_screen_info=%7B%22fullWidth%22%3A1920%2C%22fullHeight%22%3A5112%2C%22visibleWidth%22%3A1920%2C%22visibleHeight%22%3A947%7D; apbct_headless=false; ct_checked_emails=0; ct_checked_emails_exist=0; ct_mouse_moved=true; ct_has_scrolled=true; abh_tab=#abh_about; apbct_timestamp=1761826986; apbct_site_landing_ts=1761826983; apbct_prev_referer=https%3A%2F%2Fpluggedingolf.com%2Fcategory%2Freviews%2Fputters%2F; apbct_cookies_test=%257B%2522cookies_names%2522%253A%255B%2522apbct_timestamp%2522%252C%2522apbct_prev_referer%2522%255D%252C%2522check_value%2522%253A%25227f32665451ba495aa2885d594d0c84ff%2522%257D; apbct_page_hits=2' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
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
    if not next_url and not context.get('restart_revlist'):
        time.sleep(600)
        time1 = int(time.time())
        time2 = time1 + random.randint(0, 50)
        session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS.format(time1=time1, time2=time2)), process_revlist, dict(context, restart_revlist=True))

    elif next_url:
        time.sleep(10)
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    if not data.xpath('//div[@class="elementor-widget-container" and h2]/p') and not context.get('restart_review'):
        time.sleep(600)
        time1 = int(time.time())
        time2 = time1 + random.randint(0, 50)
        session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS.format(time1=time1, time2=time2)), process_review, dict(context, restart_review=True))
        return

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
