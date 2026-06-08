from agent import *
from models.products import *


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Alt-Used: blog.snyd.dk' -H 'Connection: keep-alive' -H 'Cookie: ct_ps_timestamp=1780908294; apbct_site_landing_ts=1780907937; apbct_cookies_test=%257B%2522cookies_names%2522%253A%255B%2522ct_ps_timestamp%2522%252C%2522apbct_prev_referer%2522%255D%252C%2522check_value%2522%253A%252209753438ff0ebaacf7e25d2ec682011d%2522%257D; apbct_page_hits=2; apbct_site_referer=0; ct_sfw_pass_key=d2aec8ce74e95afb13873d8ead36b52c0; ct_checkjs=428848875; ct_fkp_timestamp=1780908303; ct_pointer_data=%5B%5B422%2C1191%2C30%5D%2C%5B408%2C1234%2C1087%5D%2C%5B391%2C1223%2C1387%5D%2C%5B391%2C1215%2C1407%5D%2C%5B430%2C1228%2C1567%5D%2C%5B580%2C1373%2C1713%5D%2C%5B640%2C1323%2C1874%5D%2C%5B652%2C1316%2C2020%5D%2C%5B665%2C1269%2C2181%5D%2C%5B659%2C1216%2C2341%5D%2C%5B652%2C1189%2C2488%5D%2C%5B641%2C1163%2C2717%5D%2C%5B653%2C1176%2C2804%5D%2C%5B630%2C1213%2C2967%5D%2C%5B593%2C1301%2C3132%5D%2C%5B593%2C1303%2C3550%5D%2C%5B592%2C1304%2C4176%5D%2C%5B591%2C1304%2C7802%5D%2C%5B587%2C1298%2C7823%5D%2C%5B579%2C1293%2C8116%5D%2C%5B579%2C1292%2C8318%5D%2C%5B257%2C832%2C18948%5D%2C%5B257%2C833%2C19240%5D%2C%5B252%2C851%2C19401%5D%2C%5B209%2C780%2C19560%5D%2C%5B166%2C836%2C19721%5D%2C%5B160%2C845%2C20806%5D%2C%5B172%2C1049%2C21028%5D%2C%5B162%2C1087%2C21121%5D%2C%5B159%2C1117%2C21268%5D%2C%5B162%2C1132%2C21428%5D%2C%5B162%2C1131%2C23109%5D%2C%5B162%2C1119%2C23135%5D%2C%5B162%2C801%2C23283%5D%2C%5B173%2C581%2C23442%5D%2C%5B174%2C533%2C24978%5D%2C%5B177%2C549%2C25016%5D%2C%5B194%2C771%2C25176%5D%2C%5B205%2C781%2C25323%5D%2C%5B215%2C789%2C25484%5D%2C%5B217%2C792%2C25670%5D%2C%5B217%2C861%2C25803%5D%2C%5B222%2C892%2C25963%5D%2C%5B300%2C1015%2C26110%5D%2C%5B353%2C1061%2C26552%5D%2C%5B353%2C1060%2C26765%5D%5D; ct_timezone=3; ct_screen_info=%7B%22fullWidth%22%3A1920%2C%22fullHeight%22%3A2770%2C%22visibleWidth%22%3A1920%2C%22visibleHeight%22%3A947%7D; apbct_headless=false; ct_checked_emails=0; ct_mouse_moved=true; ct_has_scrolled=true; apbct_prev_referer=http%3A%2F%2Fblog.snyd.dk%2F' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('http://blog.snyd.dk/', force_charset='utf-8', use='curl', options=OPTIONS), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8', use='curl', options=OPTIONS), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl', options=OPTIONS), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.category = 'Games'

    product.name = data.xpath('//p[contains(strong/text(), "Spil anmeldt:")]/text()').string(multiple=True)
    if not product.name:
        product.name = context['title'].split(' - ')[0].strip()

    product.ssid = data.xpath('//input[@id="comment_post_ID"]/@value').string()
    if not product.ssid:
        product.ssid = product.url.split('/')[-1].replace('.html', '')

    platform = data.xpath('//p[contains(strong/text(), "Platform:")]/text()').string(multiple=True)
    if platform:
        product.category += '|' + platform.replace(' (Microsoft, Mac og Linux)', '').replace(' / ', '/').replace(', ', '/')

    genre = data.xpath('//p[contains(strong/text(), "Genre:")]/text()').string(multiple=True)
    if genre:
        product.category += '|' + genre.replace(', ', '/')

    product.manufacturer = data.xpath('//p[contains(strong/text(), "Udvikler:")]/text()').string(multiple=True)
    if not product.manufacturer:
        product.manufacturer = data.xpath('//p[contains(strong/text(), "Udgiver:")]/text()').string(multiple=True)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="meta-author"]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(strong/text(), "Anmelderens karakter:")]/text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split('/')[0].strip()
        if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    excerpt = data.xpath('//div[@class="post"]/div/p[not(regexp:test(strong/text(), "Spil anmeldt\:|Anmeldelse af\:|Anmelderens karakter\:|Udgiver\:|Udvikler\:|Udgivelsesdato\:|Platform\:|Genre\:"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
