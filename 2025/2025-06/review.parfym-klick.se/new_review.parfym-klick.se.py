from agent import *
from models.products import *


XCAT = ['Aftershave', 'Inspiration']


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.parfym-klick.se/', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@id="navBar"]/div[@class="navCategory withDropdown"]/a')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url + '?l=144', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    sub_cats = data.xpath('//a[@class="filterItem subItem"]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('text()').string(multiple=True).split('(')[0].strip()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))
    else:
        sub_name = data.xpath('//a[@class="filterItem subItem selected"]/text()').string(multiple=True)
        if sub_name:
            context['cat'] += '|' + sub_name.split('(')[0].strip()
            process_prodlist(data, context, session)


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="productBox"]')
    for prod in prods:
        name = prod.xpath('.//div[@class="fullName"]//text()').string(multiple=True)
        url = prod.xpath('.//a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//meta[@itemprop="sku"]/@content').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@id="prodDetails"]/a/text()').string()

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('//div[@class="reviewAge"]/text()').string()

        author = rev.xpath('div[@class="reviewAuthor"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('meta[@itemprop="reviewRating"]/@value').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('div[@class="reviewTitle"]/text()').string()
        excerpt = rev.xpath('div[@class="reviewContent"]/text()').string()
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
