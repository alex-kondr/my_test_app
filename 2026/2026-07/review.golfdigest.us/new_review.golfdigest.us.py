from agent import *
from models.products import *


XCAT = ['All']
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: usprivacy=1---; AMCVS_9AE0F0145936E3790A495CAA%40AdobeOrg=1; __ds_loc_country=UA; __ds_loc_state=KV' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def run(context, session):
    session.queue(Request('https://www.golfdigest.com/equipment/hot-list', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_catlist, dict())
    session.queue(Request('https://www.golfdigest.com/hot-list-2023/', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul/li[contains(@class, "subnav-ite")]/a')
    if not cats:
        cats = data.xpath('//a[contains(@class, "StoryCard") and @data-pub-date]')

    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True) or cat.xpath('@aria-label').string()
        url = cat.xpath('@href').string()

        if name and name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="o-ClubInfoBox__m-Details"]')
    if not revs:
        revs = data.xpath('//div[contains(@class, "ReviewList") and not(.//p[contains(., "Next")])]/a')

    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_review, dict(context, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[regexp:test(@class, "AssetTitle|productTitle")]//text()').string(multiple=True)
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Golf Clubs|' + context['cat']
    product.manufacturer = data.xpath('//h2[@class="brand"]/text()').string()

    product.url = data.xpath('//a[contains(@class, "buy-link") and not(contains(text(), "golf galaxy"))]/@href[not(contains(., "/click-"))]').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = context['url']
    review.ssid = product.ssid

    date_info = data.xpath('//script[contains(., "origPubDate =")]/text()').string()
    if date_info:
        review.date = date_info.split("origPubDate = '")[-1].split('T')[0]

    grade_overall = data.xpath('//span[contains(@class, "RatingDisplay--rating")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//div[@class="o-Rating" and .//h6]')
    for grade in grades:
        grade_name = grade.xpath('.//h6/text()').string()
        grade_val = grade.xpath('@data-score').string()
        if not grade_val:
            grade_val = grade.xpath('div/@aria-label').string()

        grade_val = grade_val.split(' out ')[0].split(' of ')[0]
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[h2[contains(., "Why We Like It")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    summary = data.xpath('//div[@class="productDescription"]/p//text()[not(regexp:test(., "WHAT IT DOES|WHY WE LIKE IT|Read more|WHAT YOU NEED TO KNOW"))]').string(multiple=True)

    next_url = data.xpath('//a[contains(text(), "Read more")]/@href').string()
    if next_url:
        if summary:
            review.add_property(type='summary', value=summary)

        session.do(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_review_next, dict(product=product, review=review))
        return

    if summary:
        review.add_property(type='excerpt', value=summary)

        product.reviews.append(review)

    revs = data.xpath('//section[contains(@class, "m-Feedback")]')
    for rev in revs:
        review = Review()
        review.type = 'pro'
        review.title = product.name
        review.url = context['url']
        review.ssid = product.ssid

        author = rev.xpath('following-sibling::div[1]//span[contains(@class, "a-Name")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following-sibling::div[1]//span[contains(@class, "Handicap")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Handicap', '')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=17.0))

        excerpt = rev.xpath('following-sibling::div[2]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    review.title = data.xpath('//h1[regexp:test(@class, "AssetTitle|productTitle")]//text()').string(multiple=True)
    review.date = data.xpath('//div[contains(@class, "AssetPublishDate")]//text()').string(multiple=True)

    author = data.xpath('//span[contains(@class, "a-Name")]//text()').string(multiple=True)
    author_url = data.xpath('//span[contains(@class, "a-Name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "articleBody")]/div/p[not(regexp:test(., "PRICE:|RELATED:"))]//text()[not(regexp:test(., "WHAT IT DOES|WHY WE LIKE IT|Read more|WHAT YOU NEED TO KNOW"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
