from agent import *
from models.products import *
import simplejson
import re


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    options = """--globoff --compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept-Encoding: deflate' -H 'Cookie: _k5a=61@{"u":[{"uid":"VqQEsRmDIN2vy4KD","ts":1759480410},1759570410]}'"""
    session.queue(Request('https://api.mobil.se/api/v1/article/?orderBy=published&htmlText=1&query=visibility_status:P%20AND%20published:[*%20NOW]%20AND%20NOT%20hidefromfp_time:[*%20NOW]%20AND%20(tag%3Aprodukttester%20OR%20tag%3A%22j%C3%A4mf%C3%B6rande%20tester%22)%20AND%20(tag%3Aapple%20OR%20tag%3Asamsung%20OR%20tag%3Axiaomi%20OR%20tag%3Agoogle%20OR%20tag%3Asony%20OR%20tag%3Amotorola%20OR%20tag%3Aoneplus%20OR%20tag%3Ahuawei%20OR%20tag%3Alenovo%20OR%20tag%3Anokia%20OR%20tag%3Anothing%20OR%20tag%3Aikea%20OR%20tag%3A%22andra%20tillverkare%22)%20AND%20(tag%3Asurfplatta%20OR%20tag%3Atelefon%20OR%20tag%3A%22h%C3%B6rlurar%20headset%22%20OR%20tag%3Ah%C3%B6gtalare%20OR%20tag%3A%22klockor%20armband%22%20OR%20tag%3A%22smarta%20hemmet%22%20OR%20tag%3Aoutdoor)&fields=*,-bodytext,-ai_*,-bodytextHTML&limit=280&site_id=2', use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('result', [])
    for rev in revs:
        title = rev.get('title')
        url = 'https://www.mobil.se' + rev.get('published_url')

        if not re.search(r'mobiler för| de bästa| jättetest|\d+ modeller |jämförande test', title, flags=re.U|re.I) and 'jämförande test' not in title.lower() and 'jättetest' not in title.lower() and 'de bästa' not in title.lower() and 'mobiler för' not in title.lower() and 'bäst under' not in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    revs_cnt = revs_json.get('totalCount', 0)
    offset = context.get('offset', 0) + 280
    if int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        options = """--globoff --compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept-Encoding: deflate' -H 'Cookie: _k5a=61@{"u":[{"uid":"VqQEsRmDIN2vy4KD","ts":1759480410},1759570410]}'"""
        next_url = 'https://api.mobil.se/api/v1/article/?orderBy=published&htmlText=1&query=visibility_status:P%20AND%20published:[*%20NOW]%20AND%20NOT%20hidefromfp_time:[*%20NOW]%20AND%20(tag%3Aprodukttester%20OR%20tag%3A%22j%C3%A4mf%C3%B6rande%20tester%22)%20AND%20(tag%3Aapple%20OR%20tag%3Asamsung%20OR%20tag%3Axiaomi%20OR%20tag%3Agoogle%20OR%20tag%3Asony%20OR%20tag%3Amotorola%20OR%20tag%3Aoneplus%20OR%20tag%3Ahuawei%20OR%20tag%3Alenovo%20OR%20tag%3Anokia%20OR%20tag%3Anothing%20OR%20tag%3Aikea%20OR%20tag%3A%22andra%20tillverkare%22)%20AND%20(tag%3Asurfplatta%20OR%20tag%3Atelefon%20OR%20tag%3A%22h%C3%B6rlurar%20headset%22%20OR%20tag%3Ah%C3%B6gtalare%20OR%20tag%3A%22klockor%20armband%22%20OR%20tag%3A%22smarta%20hemmet%22%20OR%20tag%3Aoutdoor)&fields=*,-bodytext,-ai_*,-bodytextHTML&limit=280&site_id=2&page=' + str(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=options, max_age=0), process_revlist, dict(offset=offset, page=next_page))


def process_review(data: Response, context: dict[str, str], session: Session):
    if data.xpath('count(//p[regexp:test(text(), "Betyg: \d+")])') > 2:
        return

    product = Product()
    product.name = context['title'].replace('Långtidstest: ', '').replace(' i långtidstest', '').replace('Exklusivt: ', '').replace('Stort test: ', '').replace('Test: ', '').replace('Testad: ', '').replace(' testade', '').split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = 'Teknik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/span[@itemprop="name"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('@')[0].replace('mailto:', '')
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//dl[dt[contains(., "Betyg")]]/dd[not(@class)]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('(//div[@class="score"]/dl)[1]/dt[not(contains(., "Betyg"))]')
    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = float(grade.xpath('(following-sibling::dd[not(@class)])[1]/text()').string().split('/')[0].replace('%', ''))
        best = 10.0
        if grade_val > 10:
            best = 100.0

        if grade_name == 'Totalbetyg' and not grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_val), best=best))
        elif grade_name != 'Totalbetyg':
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=best))

    pros = data.xpath('(//div[@class="pros"])[1]//text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[@class="cons"])[1]//text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[contains(@class, "subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "bodytext")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
