from agent import *
from models.products import *
import HTMLParser
import time
import random


h = HTMLParser.HTMLParser()
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: aws-waf-token=e5789eea-52cd-44fb-9e92-9621ceff092f:DQoAm3JqELDNIwAA:+DQU62rKKfdni6/iLUNtpuzaFlZxoM27xvJ0onc+kbFwYhBCoE3j2DVSz1Y6dTM25fxAChRVg2pD4RIzCwM1yv+n57o2COPnXuXIYJQ4JMqDChnvFg7qU+ItialDS+N7N7nQbN2ALU4vUbCHEyoLxQR9tpQoCqZ/fN/qT8v017Bzf16Lm9MezDAdkN6VoEEUBTWZ88O2Qo6O+6JwlWUsabdmOGly7GmAyMZ55nZ5CGWyeKfxP0YWt/oComlic6iEBliLP39QmNCufIn9ldQeICROxworWzsKfhlh4I9gOC/etss67slsAg==; consentUUID=eaeb9499-43ee-4caa-9039-5ad7e64b88f8_61; consentDate=2026-10-07T13:27:21.925Z' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.whatcar.com/reviews', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    cats = data.xpath('//ul[contains(@class, "category")]/li//a[@hreflang]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url+'?page=0', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//h3/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_review, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.manufacturer = data.xpath('//nav[@role="navigation"]//a[contains(@href, "/make/")]/text()').string()

    product.ssid = context['url'].split('/')[-1]
    if 'review' in product.ssid:
        product.ssid = product.name.lower().replace(' ', '_').replace(':', '_')

    product.url = data.xpath('//a[contains(., "New car deals") and @data-bi="cta-click"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="author-date"]/span[not(contains(., "Updated"))]/text()').string()

    author = data.xpath('//div[contains(@class, "author-name")]/a[contains(@class, "author-link")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "author-name")]/a[contains(@class, "author-link")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "main-title")]//div/@data-rating').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[contains(div/span, "Overview")]/div/@data-rating').string()

    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//h2[contains(@class, "review-chapter-heading") and following-sibling::div[1][contains(@class, "rating-justify-left")]]')
    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = grade.xpath('following-sibling::div[1][contains(@class, "rating-justify-left")]/div/@data-rating').string()
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[contains(h3, "Strengths") or contains(h3, "Pros")]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(h3, "Weaknesses") or contains(h3, "Cons")]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "main-title")]/h2//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "verdict-body")]//text()').string(multiple=True)
    if conclusion:
        conclusion = h.unescape(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "section-content")]/p[not(preceding::h2[regexp:test(., "Buy it if|Don’t buy it if")] or contains(., "For all the latest reviews"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = h.unescape(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)