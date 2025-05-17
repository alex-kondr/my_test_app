from agent import *
from models.products import *


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://cairosales.com/ar/', use='curl', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "mm_columns_ul_tab")]/li')
    for cat in cats:
        name = cat.xpath('div//span/text()').string(multiple=True)

        sub_cats = cat.xpath('ul//li[@class="mm_blocks_li" and .//ul]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div/h4//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('.//li/a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url, use='curl', max_age=0), process_category, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_category(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//ul[contains(@class, "product_list")]/li')
    for prod in prods:
        prod_ssid = prod.xpath('@data-id-product').string()
        url = prod.xpath('.//h5/a/@href').string()

        revs = prod.xpath('.//div[contains(@class, "rating-star")]')
        if revs:
            session.queue(Request(url, use='curl', max_age=0), process_product, dict(context, prod_ssid=prod_ssid, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_category, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    name = data.xpath('//div[contains(@class, "center")]/h1//text()').string(multiple=True)
    if not name:
        return

    product = Product()
    product.name = name.replace(u'\uFEFF', '').strip()
    product.url = context['url']
    product.ssid = context['prod_ssid']
    product.sku = product.ssid
    product.category = context['cat']

    manufacturer = data.xpath("//meta[@property='product:brand']/@content").string()
    if manufacturer:
        product.manufacturer = manufacturer.strip("-")

    mpn = data.xpath('//p[label[contains(., "الموديل")]]/span/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs = data.xpath('//div[div[contains(@class, "review-line-name")]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.date = rev.xpath('.//meta/@content').string()

        author = rev.xpath('div[contains(@class, "name")]/strong/span/text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//div[contains(@class, "rating")]/input[@checked="checked"])')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//div[@class="review-line-comment"]/p/strong//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="review-line-comment"]/p[not(.//strong)]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' +-*.')) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' +-*.')
            if len(excerpt) > 2 and not any((True for char in ['e', 'y', 'u', 'i', 'o', 'a'] if char in excerpt.lower())):
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
