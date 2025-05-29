from agent import *
from models.products import *
import re


XCAT = ['SALE', 'Brands', 'Guide']


def run(context, session):
    session.queue(Request('https://www.ozscopes.com.au/', use='curl', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level0")]')
    for cat in cats:
        name = cat.xpath("a//text()").string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('.//ul/li[contains(@class, "level1")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string(multiple=True)

                if 'Brands' not in sub_name:
                    sub_cats1 = sub_cat.xpath('.//ul/li[contains(@class, "level2")]/a')

                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                            url = sub_cat1.xpath('@href').string()

                            if not any([sub_name1.startswith('All '), sub_name1.startswith('ALL ')]):
                                sub_name_ = ('|' + sub_name) if 'by types' not in sub_name.lower() else ''
                                session.queue(Request(url + '?product_list_limit=36', use='curl', force_charset='utf-8'), process_category, dict(context, url=url, cat=name + sub_name_ + '|' + sub_name1))
                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url + '?product_list_limit=36', use='curl', force_charset='utf-8'), process_category, dict(context, url=url, cat=name + '|' + sub_name))


def process_category(data, context, session):
    prods = data.xpath('//li[contains(@class, "product-item")]')
    for prod in prods:
        name = prod.xpath('.//strong/a//text()').string(multiple=True)
        url = prod.xpath('.//strong/a/@href').string()

        revs_cnt = prod.xpath('.//div[@class="reviews-actions"]/a/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@title="Next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//form[@data-product-sku]//input[@name="product"]/@value').string()
    product.sku = product.ssid
    product.category = context['cat']

    mpn = data.xpath('//form/@data-product-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_url = 'https://www.ozscopes.com.au/review/product/listAjax/id/' + product.ssid
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[contains(@class, "review-item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//time/@datetime").string()

        author = rev.xpath('.//strong[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        title = rev.xpath('.//div[@class="review-title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="review-content"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            grade_overall = re.search(r' \d+\.?\d/\\d+|\d+\.?\d/\d+ ', excerpt)
            if grade_overall:
                grade_overall, grade_best = grade_overall.group(0).split('/')
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(grade_best)))

            excerpt = re.sub(r' \d+\.?\d/\d+|\d+\.?\d/\d+ ', '', excerpt)
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@title="Next"]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
