from agent import *
from models.products import *
import time


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: ct_sfw_pass_key=2b3ea3abfb10ee5236a808463c1069e80; ct_checkjs=277158b25d470642b40a35e629286e2b97386d97767df0b71258a1e48f326304; ct_ps_timestamp=1761223971; ct_fkp_timestamp=1761223990; ct_pointer_data=%5B%5B202%2C1224%2C824%5D%2C%5B215%2C1224%2C842%5D%2C%5B332%2C1266%2C1159%5D%2C%5B328%2C1267%2C1308%5D%2C%5B321%2C1261%2C2057%5D%2C%5B301%2C1222%2C2091%5D%2C%5B327%2C494%2C2257%5D%2C%5B324%2C406%2C4341%5D%2C%5B328%2C406%2C4591%5D%2C%5B329%2C408%2C4607%5D%2C%5B340%2C422%2C4757%5D%2C%5B348%2C430%2C4907%5D%2C%5B354%2C440%2C5124%5D%2C%5B30%2C460%2C18157%5D%2C%5B106%2C396%2C18172%5D%2C%5B313%2C199%2C18339%5D%2C%5B283%2C160%2C18489%5D%2C%5B215%2C216%2C18673%5D%2C%5B209%2C222%2C19135%5D%2C%5B494%2C317%2C19888%5D%2C%5B478%2C315%2C19910%5D%2C%5B10%2C583%2C24789%5D%2C%5B271%2C764%2C24905%5D%2C%5B316%2C838%2C25055%5D%2C%5B372%2C817%2C25221%5D%2C%5B583%2C585%2C25371%5D%2C%5B324%2C274%2C230031%5D%2C%5B21%2C305%2C230080%5D%2C%5B14%2C559%2C1787138%5D%2C%5B294%2C578%2C1787302%5D%5D; ct_timezone=3; ct_screen_info=%7B%22fullWidth%22%3A1536%2C%22fullHeight%22%3A10518%2C%22visibleWidth%22%3A1536%2C%22visibleHeight%22%3A731%7D; apbct_headless=false; ct_checked_emails=0; ct_checked_emails_exist=0; ct_mouse_moved=true; ct_has_scrolled=true; apbct_timestamp=1761223971; apbct_site_landing_ts=1761219466; apbct_cookies_test=%257B%2522cookies_names%2522%253A%255B%2522apbct_timestamp%2522%255D%252C%2522check_value%2522%253A%25227762dcf71490bd0c7caa04f86504b753%2522%257D; apbct_page_hits=2; apbct_site_referer=0' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://pluggedingolf.com/', use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[a[contains(text(), "Reviews")]]/ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul/li/a')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string()
                url = sub_cat.xpath('@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.xpath('a/@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        time.sleep(10)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, dict(context))


def process_review(data, context, session):
    if not data.xpath('//div[@class="elementor-widget-container" and h2]/p') and not context.get('restart'):
        time.sleep(600)
        session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, restart=True))

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
