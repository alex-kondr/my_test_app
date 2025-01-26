from agent import *
from models.products import *
import simplejson


XCAT = ['Offerte', 'Esperienze']


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://www.bernabei.it'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "level0")]/a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//dd[@class="champagne_tipologia"]//li/a')
    if not sub_cats:
        sub_cats = data.xpath('//dd[@class="tipologia"]//li/a')
    if not sub_cats:
        process_prodlist(data, context, session)

    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('text()').string().strip('()')
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="item-title"]/a')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//a[@class="button next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[@itemprop="name"]/text()').string()
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="product"]/@value').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="spec_produttore"]/span/text()').string()

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('sku')

    revs_cnt = data.xpath('//meta[@itemprop="reviewCount"]/@content').string()
    if revs_cnt and revs_cnt.isdigit() and int(revs_cnt) > 0:
        revs_url = 'https://www.bernabei.it/bernabei_customization/index/getreviewsprodotto?product_id=' + product.ssid
        session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[contains(@class, "recensione voto")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('small[@class="date"]/text()').string()

        author = rev.xpath('.//div[@class="autore-recensione"]/span/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('@class').string()
        if grade_overall:
            grade_overall = float(grade_overall.replace('recensione voto', '')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        helpful = rev.xpath('.//a[@class="voteup"]/span/text()').string()
        if helpful and helpful.isdigit() and int(helpful) > 0:
            review.add_property(type='helpful_votes', value=int(helpful))

        not_helpful = rev.xpath('.//a[@class="votedown"]/span/text()').string()
        if not_helpful and not_helpful.isdigit() and int(not_helpful) > 0:
            review.add_property(type='not_helpful_votes', value=int(not_helpful))

        title = rev.xpath('.//div[@class="titolo-recensione"]/text()').string()
        excerpt = rev.xpath('.//div[@class="test-recensione"]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' \n\r\t.+-')) > 1:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' \n\r\t.+-')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = rev.xpath('.//div[@class="votes"]/@rel').string()
                if not review.ssid:
                    review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# not next page
