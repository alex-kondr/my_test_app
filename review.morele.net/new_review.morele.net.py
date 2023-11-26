from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.morele.net/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul[@data-level="current"]/li')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        sub_cats = cat.xpath('.//ul[@class="cn-row"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/text()').string()

            sub_cats1 = sub_cat.xpath('ul/li/a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string()

                    url = sub_cat1.xpath('@href').string()
                    if ',,,0,,,,' not in url:
                        url = url + ',,,,,,,rr,1,,,,/1/'

                        cat = name + '|' + sub_name
                        if sub_name1 not in cat:
                            cat = name + '|' + sub_name + '|' + sub_name1

                        session.queue(Request(url), process_prodlist, dict(cat=cat))
            else:
                url = sub_cat.xpath('a/@href').string() + ',,,,,,,rr,1,,,,/1/'
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="cat-product card"]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('@data-product-name').string()
        product.category = context['cat']
        product.ssid = prod.xpath('@data-product-id').string()
        product.manufacturer = prod.xpath('@data-product-brand').string()
        product.url = prod.xpath('.//a[@class="productLink"]/@href').string()

        revs_cnt = prod.xpath('.//span[@class="rating-count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            revs_cnt = int(revs_cnt.strip('()'))
            session.queue(Request(product.url  + "?sekcja=reviews&reviews_page=1"), process_reviews, dict(product=product, revs_cnt=revs_cnt))
        else:
            return

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    if not context.get('page'):
        product.sku = data.xpath('//span[@itemprop="sku"]//text()').string()

        ean = data.xpath('//span[@itemprop="gtin13"]//text()').string()
        if ean:
            product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()
        review.date = rev.xpath('.//div[@class="rev-date"]//text()').string()

        author = rev.xpath('.//div[@class="rev-author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//i[@class="icon-purchase-verified"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[@class="positive-rate-count"]//text()').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[@class="negative-rate-count"]//text()').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        pros = rev.xpath('.//ul[@class="rev-good"]/li[position() > 1]')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True).replace('+', '').strip()
            if pro:
                review.add_property(type="pros", value=pro)

        cons = rev.xpath('.//ul[@class="rev-bad"]/li[position() > 1]')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True).replace('-', '').strip()
            if con:
                review.add_property(type="cons", value=con)

        excerpt = rev.xpath('.//div[@class="rev-desc"]//text()').string(multiple=True)
        if excerpt and len(excerpt) > 1:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0)
    if offset < context['revs_cnt']:
        offset = offset + 20
        next_page = context.get('page', 1) + 1
        next_url = product.url + '?sekcja=reviews&reviews_page=' + str(next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, page=next_page, offset=offset))

    elif product.reviews:
        session.emit(product)
