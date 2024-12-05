from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.digixo.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class="cbp-hrtitle"]')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        sub_cats = cat.xpath('.//div[@class="cbp-hrsub-inner"]/div')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('h4//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('ul//a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string(multiple=True)
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-txt") and .//i[contains(@class, "fa-star")]]')
    for prod in prods:
        brand = prod.xpath('div[@class="brandname"]/text()').string(multiple=True)
        name = prod.xpath('div/span[@class="entityname"]/text()').string(multiple=True)
        url = prod.xpath('.//a/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, brand=brand, url=url))

    next_url = data.xpath('//a[@title="Aller à la page suivante"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/p')[-1].split('-')[0]
    product.category = context['cat']
    product.manufacturer = context['brand']

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type="id.ean", value=ean)

    revs_url = 'https://www.digixo.com/v1/product/{ssid}/getreviews'.format(ssid=product.ssid)
    session.queue(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = simplejson.loads(data.content)
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.get('pseudo')
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('note')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = rev.get('comment_pos')
        if pros:
            pros = pros.split('\r\n')
            for pro in pros:
                pro = pro.strip()
                review.add_property(type='pros', value=pro)

        cons = rev.get('comment_neg')
        if cons:
            cons = cons.split('\r\n')
            for con in cons:
                con = con.strip()
                review.add_property(type='cons', value=con)

        title = rev.get('titre')
        excerpt = rev.get('comment')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\r\n', '').strip()

            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
