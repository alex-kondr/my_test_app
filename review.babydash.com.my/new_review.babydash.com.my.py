from agent import *
from models.products import *


XCAT = ['Gifts', 'Sale', 'Brands', 'Formula & Food', 'View Brands']


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.babydash.com.my/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath("//div[@class='top-container']/ol/li//a")
    for cat in cats:
        name = cat.xpath(".//text()").string(multiple=True)
        url = cat.xpath('@href').string()

        if name and name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    sub_cats = data.xpath('//dl[dt[contains(., "Category")]]//ol[@class="items"]/li')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('a/text()').string(multiple=True)

        if sub_name and sub_name not in XCAT:
            sub_cats1 = sub_cat.xpath('ol/li//a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string()
                url = sub_cat1.xpath('@href').string()

                if sub_name1 and sub_name1 not in XCAT:
                    if sub_name1 != sub_name:
                        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+sub_name+'|'+sub_name1))
                    else:
                        session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath("//a[@class='product-item-link']")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath("//a[@class='link next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name'].replace(u'\uFEFF', '').replace('bbluv: ', '').strip()
    product.ssid = data.xpath("//div[@class='product-info-price']/div/@data-product-id").string()
    product.sku = product.ssid
    product.category = context['cat']
    product.url = context['url']

    ean = data.xpath("//div[@itemprop='sku']//text()").string()
    if ean:
        ean = ean.split('+')[0].replace(u'\uFEFF', '').split()[0].strip()
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs_cnt = data.xpath("//span[@itemprop='reviewCount']/text()").string()
    if revs_cnt:
        reviews_url = "https://www.babydash.com.my/review/product/listAjax/id/" + str(product.ssid)
        session.do(Request(reviews_url), process_reviews, dict(context, product=product))


def process_reviews(data, context, session):
    strip_namespace(data)

    product = context["product"]

    revs = data.xpath('//li[contains(@class, "review-item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//strong[@itemprop="author"]/text()').string()
        if author:
            author = author.replace(u'\uFEFF', '').strip()
            review.authors.append(Person(name=author, ssid=author))

        grades = rev.xpath('.//div[@itemprop="reviewRating"]')
        for grade in grades:
            grade_name = grade.xpath('span/span/text()').string()
            grade_val = float(grade.xpath('div/@title').string().replace('%', '')) / 20
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

        title = rev.xpath('.//div[@class="review-title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="review-content"]//text()').string(multiple=True)
        if excerpt:
            if title:
                review.title = title.replace(u'\uFEFF', '').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace(u'\uFEFF', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
