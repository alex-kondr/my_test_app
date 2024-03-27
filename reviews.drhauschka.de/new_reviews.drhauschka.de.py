from agent import *
from models.products import *


XCAT = ['Behandlungen ', 'Beratung ', 'Hautberatungsteam', 'Werte', 'Magazin']


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.drhauschka.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="menu--container"]')
    for cat in cats:
        name = cat.xpath('.//a[@class="button--category"]/@title').string(multiple=True).replace('Zur Kategorie', '').strip()

        if name not in XCAT:
            sub_cats = cat.xpath('.//li[contains(@class, "item--level-0")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/text()').string()

                if sub_name:
                    sub_cats1 = sub_cat.xpath('.//li[contains(@class, "item--level-1")]/a')

                    if sub_cats1:
                        for sub_cat1 in sub_cats1:
                            sub_name1 = sub_cat1.xpath('text()').string()
                            url = sub_cat1.xpath('@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1, prods_url=url))
                    else:
                        url = sub_cat.xpath('a/@href').string()
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name, prods_url=url))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product--box"]')
    for prod in prods:
        ssid = prod.xpath('@data-ordernumber').string()
        name = prod.xpath('.//a[@class="product--title"]/text()').string()
        url = prod.xpath('.//a[@class="product--title"]/@href').string()
        session.queue(Request(url), process_product, dict(context, ssid=ssid, name=name, url=url))

    pages_cnt = data.xpath('//div/@data-pages').string()
    next_page = context.get('page', 1) + 1
    if pages_cnt and int(pages_cnt) >= next_page:
        next_url = context['prods_url'] + '?p=' + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    revs_cnt = data.xpath('//span[@class="rating--count"]/text()').string()
    if not revs_cnt or int(revs_cnt) < 1:
        return

    product = Product()
    product.name = context['name']
    product.ssid = context['ssid']
    product.url = context['url']
    product.category = context['cat']
    product.sku = data.xpath('//div[contains(@class, "entry--sku")]/span/text()').string()

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 12:
        product.add_property(type='id.ea', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//a[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Author(name=author, ssid=author))

        grade_overall = rev.xpath('.//meta[@itemprop="ratingValue"]/@content').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = rev.xpath('.//span[@class="is_amount_helpful"]/text()').string()
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[@class="is_amount_not_helpful"]/text()').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//h4[@class="content--title"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.ssid = review.digest() if author else review.digest(excerpt)

            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
