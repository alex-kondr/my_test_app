from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://www.grosbill.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//fieldset[.//li]')
    for cat in cats:
        name = cat.xpath('p//text()').string(multiple=True)

        sub_cats = cat.xpath('.//ul')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('li[@class]//span//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('li[not(@class)]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('a//text()').string(multiple=True)
                url = sub_cat1.xpath('a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="grb__liste-produit__liste__produit__information__container" and .//p[contains(., " avis)")]]')
    for prod in prods:
        name = prod.xpath('.//h2//text()').string(multiple=True)
        url = prod.xpath('.//a/@href').string().replace('+', '')
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.aspx', '')
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()
    product.sku = data.xpath('//p[contains(@id, "lbl_num_produit")]//text()').string(multiple=True)

    mpn = data.xpath('//p[contains(@id, "lbl_ref_constructeur")]//text()').string(multiple=True)
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//p[contains(@id, "code_ean")]//text()').string(multiple=True)
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="avis_commentaires__un_avis"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.xpath('.//b[@class="un_avis__nom"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="un_avis__note"]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.strip('()').split('/')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath('.//div[@class="un_avis__commentaire"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
