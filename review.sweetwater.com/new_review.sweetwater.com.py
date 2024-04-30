from agent import *
from models.products import *


XCAT = ['Accessories', 'Content Creators']
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Referer: https://www.sweetwater.com/store/detail/GSMiniKOAESB--taylor-gs-mini-e-koa-natural/reviews' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'Connection: keep-alive' -H 'Cookie: _pxhd=; SSID=CQAdMh0AAAAAAACZhy9m_pWCCJmHL2YDAAAAAAAAAAAAf5MwZgCwtg; SSRT=W5owZgQBAA; sws-fonts=1; sws-gwpop=1; sws-device-time=1714459519; sws-device-id=937618376; sws-device-token=2d5ca8f801b5f05a2a814f2a870ef5a38d84aadd; sws_srl=eyJ2aWV3ZWQiOnsiR1NNaW5pS09BRVNCIjp7InRpbWUiOjE3MTQzOTg5NzMsInNlcmlhbCI6IjIyMDUwNTMwNzYifX19; SSSC=730.G7363253007116572158.3|0.0; refserv=Direct; sws-fv=1'"""


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.sweetwater.com', use='curl', options=OPTIONS, max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="assets-site-header__nav-menu-item mn-top-level"]')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        if name and name not in XCAT:
            sub_cats = cat.xpath('.//a[contains(@id, "mn-col-headline")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('text()').string(multiple=True)
                sub_name = sub_name if 'More ' not in sub_name else ''

                sub_cats1 = sub_cat.xpath('following-sibling::div[contains(@data-headline-id, "mn-col-headline")][1]/a')
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string(multiple=True)

                    if 'All ' not in sub_name1:
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url + '?sb=reviews', use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(cat=(name + '|' + sub_name + '|' + sub_name1).replace('||', '|')))
                else:
                    url = sub_cat.xpath('@href').string()
                    session.queue(Request(url + '?sb=reviews', use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(cat=(name + '|' + sub_name).replace('||', '|')))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-card__info"]')
    for prod in prods:
        name = prod.xpath('h2[@class="product-card__name"]//a/text()').string()
        ssid = prod.xpath('div/@data-serial').string()
        sku = prod.xpath('div/@data-itemid').string()
        url = prod.xpath('h2[@class="product-card__name"]//a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="rating__count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, use='curl', options=OPTIONS, max_age=0), process_product, dict(context, name=name, ssid=ssid, sku=sku, url=url))
        else:
            return

    next_url = data.xpath('//a[@class="paginate-next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = context['sku']
    product.category = context['cat']

    mpn = data.xpath('//li[.//strong[contains(., "Manufacturer")]]//span[@class="table__cell"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    session.queue(Request(product.url + '/reviews', use='curl', options=OPTIONS, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//body[h3[@class="review-customer-box__title"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author_date = rev.xpath('.//span[@class="review-customer-box__subhead"]/text()').string()
        author, date = None, None
        if author_date:
            author, date = author_date.split(' on ')

            date = date.strip()
            if date:
                review.date = date

            author = author.split('By ')[-1].split('from ')[0].strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = data.xpath('(p[@class="review-customer-box__comments"]//span[string-length() > 1]/@data-rated)[last()]').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall)))

        title = data.xpath('h3[@class="review-customer-box__title"]//span//text() ').string(multiple=True)
        excerpt = data.xpath('p[@class="review-customer-box__comments"]//span//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page