from agent import *
from models.products import *


XCAT = ["Offers", "Brands", "Customer Service", "Corporate Info"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.andertons.co.uk/sitemap'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//div[@class='dtb-sitemap__segment-content']")
    for cat in cats:
        name = cat.xpath('.//a[@aria-level="2"]/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//li[@class="h2 dtb-sitemap__segment-subtitle"]')

            for cat1 in cats1:
                cat1_name = cat1.xpath('a[@aria-level="3"]/text()').string()
                if name != cat1_name:
                    cat1_name = name + '|' + cat1_name

                url = cat1.xpath('a[@aria-level="3"]/@href').string()

                subcats = cat1.xpath('.//li[@class="h3"]/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath("text()").string()
                        url = subcat.xpath("@href").string()
                        if url:
                            session.queue(Request(url+'?pageNumber=1&orderBy=5', use='curl', options="-H 'Cookie: userPageSizePreference=48'"), process_prodlist, dict(cat=cat1_name+'|'+subcat_name))
                elif url:
                    session.queue(Request(url+'?pageNumber=1&orderBy=5', use='curl', options="-H 'Cookie: userPageSizePreference=48'"), process_prodlist, dict(cat=cat1_name))


def process_prodlist(data, context, session):
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
