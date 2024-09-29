from agent import *
from models.products import *
import simplejson


XCAT = ["Offers", "Brands"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.andertons.co.uk/sitemap/categories'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//h2[contains(., "Categories")]/following-sibling::ul/li')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li')

            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/text()').string()
                if name != sub_name:
                    sub_name = name + '|' + sub_name

                url = sub_cat.xpath('a/@href').string()

                sub_cats1 = sub_cat.xpath('ul/li/a')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath("text()").string()
                        url = sub_cat1.xpath("@href").string()
                        if url:
                            session.queue(Request(url+'?pageNumber=1&orderBy=5', use='curl', options="-H 'Cookie: userPageSizePreference=48'"), process_prodlist, dict(cat=sub_name + '|' + sub_name1))
                elif url:
                    session.queue(Request(url+'?pageNumber=1&orderBy=5', use='curl', options="-H 'Cookie: userPageSizePreference=48'"), process_prodlist, dict(cat=sub_name))


def process_prodlist(data, context, session):
    prods_json = data.xpath('//script[contains(., "JSON.pars")]/text()').string()
    if prods_json:
        prods_json = simplejson.loads(prods_json.split('JSON.parse("')[-1].split('");')[0].replace('\\"', '"'))
 
 
    prods = data.xpath('//div[@class="c-product-grid"]//div[@class="o-tile"]')
    for prod in prods:
        name = prod.xpath('.//div[contains(@class, "o-tile__row o-tile__title")]/h4/text()').string()
        url = prod.xpath('.//a[@class="o-tile__link"]/@href').string()

        revs = prod.xpath('.//div[@class="o-tile__row o-tile__reviews"]')
        if revs:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return

    prods_cnt = data.xpath('//div[@class="flex-groww"]/p/text()').string()
    if not prods_cnt:
        return

    prods_cnt = int(prods_cnt.split(' - ')[1].split(' of ')[1])
    offset = context.get('offset', 0) + 48
    if offset < prods_cnt:
        curent_page = context.get('page', 1)
        next_page = curent_page + 1
        next_url = data.response_url.replace('?pageNumber=' + str(curent_page), '?pageNumber=' + str(next_page))
        session.queue(Request(next_url, use='curl', options="-H 'Cookie: userPageSizePreference=48'"), process_prodlist, dict(context, offset=offset, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = product.url.split('/')[-1]

    mpn = data.xpath('//p[@class="o-part-number" and contains(text(), "SKU:")]/text()').string()
    if mpn:
        mpn = mpn.replace('SKU:', '').strip()
        product.add_property(type='id.manufacturer', value=mpn)

    revs = data.xpath('//div[@class="o-customer-review"]')
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.date = rev.xpath('.//span[@class="o-customer-review__date"]/text()').string()

        author = rev.xpath('.//p[@class="o-customer-review__name"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="o-review-stars"]/@title').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        grades = rev.xpath('.//p[@class="o-customer-review__rating"]/span')
        if grades:
            for grade in grades:
                name_value = grade.xpath("text()").string()
                if name_value:
                   name = name_value.split(" ")[0]
                   value = float(name_value.split(" ")[1])
                   review.grades.append(Grade(name=name, value=value, best=5.0))

        excerpt = rev.xpath('text()').string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page, all revs loaded on prod's page
