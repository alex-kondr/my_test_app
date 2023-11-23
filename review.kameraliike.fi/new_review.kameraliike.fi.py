from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request("https://www.kameraliike.fi"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//a[@class="megamenu_hover hidden-lg"]')
    cats_ = data.xpath('//div[@class="row card-griddi"]')
    for cat, cat_ in zip(cats, cats_):
        name = cat.xpath('text()').string(multiple=True)

        sub_cats = cat_.xpath('.//div[@class="card megamenu_item"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div[@class="megamenu_item_title"]/a/text()').string()

            sub_cats1 = sub_cat.xpath('.//div[@class="megamenu_subitem"]/a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text').string()
                    url = sub_cat1.xpath('@href').string()
                    session.quque(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('div[@class="megamenu_item_title"]/a/@href').string()
                session.quque(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@id="injector_container"]//div[@class="product_container"]')
    for prod in prods:
        name = prod.xpath(".//img[@title][1]//@title").string(multiple=True)
        url = prod.xpath(".//a//@href").string()

        stars_cnt = prod.xpath('count(.//img[contains(@src, "fullstar.png") or contains(@src, "emptystar.png")])')
        if stars_cnt and stars_cnt > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split("/")[-1]
    product.category = context['cat']
    product.manufacturer = context['name'].split(" ")[0]

    mpn = data.xpath("//span[@class='product_code_cont']/text()").string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)
        product.ssid = mpn

    context['product'] = product
    process_reviews(context, data, session)


def process_reviews(context, data, session):
    product = context['product']

    revs = data.xpath('//body[div[@class="review_text text-left"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.date = rev.xpath('.//span[@class="review_date"]/text()').string()

        author = rev.xpath('preceding-sibling::body[1]//span[@itemprop="author"]//text()').string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('preceding-sibling::body[1]//span[@itemprop="ratingValue"]/text()').string(multiple=True)
        if grade_overall:
            grade_overall = float(grade_overall.split('/')[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//span[@itemprop="description"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
