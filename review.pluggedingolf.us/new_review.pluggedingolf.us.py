from agent import *
from models.products import *
import time
import random


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Referer: https://pluggedingolf.com/' -H 'Cookie: ct_checkjs=277158b25d470642b40a35e629286e2b97386d97767df0b71258a1e48f326304; ct_ps_timestamp={time1}; ct_fkp_timestamp={time2}; ct_pointer_data=%5B%5B295%2C1188%2C304%5D%2C%5B300%2C1188%2C321%5D%2C%5B262%2C1214%2C504%5D%2C%5B352%2C1071%2C621%5D%2C%5B484%2C827%2C771%5D%2C%5B473%2C786%2C921%5D%2C%5B422%2C690%2C1071%5D%2C%5B356%2C624%2C1222%5D%2C%5B332%2C619%2C1371%5D%2C%5B316%2C625%2C1655%5D%2C%5B316%2C627%2C1672%5D%2C%5B316%2C628%2C2322%5D%2C%5B518%2C666%2C3375%5D%2C%5B243%2C571%2C3490%5D%2C%5B232%2C571%2C3801%5D%2C%5B232%2C573%2C3874%5D%2C%5B232%2C574%2C4170%5D%2C%5B233%2C575%2C4191%5D%2C%5B242%2C584%2C5108%5D%2C%5B434%2C590%2C5242%5D%2C%5B473%2C594%2C5443%5D%2C%5B513%2C598%2C5542%5D%2C%5B513%2C597%2C6026%5D%2C%5B511%2C595%2C6710%5D%2C%5B507%2C575%2C6743%5D%2C%5B519%2C353%2C6894%5D%2C%5B531%2C353%2C7127%5D%2C%5B532%2C375%2C7997%5D%2C%5B312%2C547%2C8094%5D%2C%5B221%2C590%2C8245%5D%2C%5B256%2C559%2C8395%5D%2C%5B536%2C113%2C8545%5D%2C%5B510%2C131%2C9396%5D%2C%5B303%2C412%2C9447%5D%2C%5B238%2C534%2C9663%5D%2C%5B243%2C569%2C9747%5D%2C%5B244%2C578%2C10380%5D%2C%5B344%2C595%2C10514%5D%2C%5B421%2C596%2C10665%5D%5D; ct_timezone=2; ct_screen_info=%7B%22fullWidth%22%3A1920%2C%22fullHeight%22%3A3195%2C%22visibleWidth%22%3A1920%2C%22visibleHeight%22%3A947%7D; apbct_headless=false; ct_checked_emails=0; ct_checked_emails_exist=0; ct_mouse_moved=true; ct_has_scrolled=true; abh_tab=#abh_about' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


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
