from agent import *
from models.products import *


XCAT = ['Angebote', 'Marken', 'Tipps & Trends', 'Zoo Marken', 'Materialien']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.dehner.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "nav-level-0")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@data-ajax-nav').string()

        if name not in XCAT:
            session.queue(Request('https://www.dehner.de' + url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//li[contains(@class, "nav-level-1")]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('.//span[@class="nav-link-wrap"]/text()').string()

        if sub_name not in XCAT:
            sub_cats1 = sub_cat.xpath('.//li[contains(@class, "nav-level-2")]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('.//div[@class="nav-item-headline"]/text()').string()

                if sub_name1 not in XCAT:
                    sub_cats2 = sub_cat1.xpath('.//li[contains(@class, "nav-level-3")]/a')
                    for sub_cat2 in sub_cats2:
                        sub_name2 = sub_cat2.xpath('text()').string()
                        url = sub_cat2.xpath('@href').string()
                        session.queue(Request(url + '?sortBy=rating'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name + '|' + sub_name2))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@itemprop="itemListElement"]')
    for prod in prods:
        name = prod.xpath('a/@title').string()
        url = prod.xpath('a/@href').string()

        revs_cnt = prod.xpath('.//span[@itemprop="reviewCount"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//div[@class="load-more-button"]/a/@data-ajax-url').string()
    if next_url:
        session.queue(Request('https://www.dehner.de' + next_url + '&sortBy=rating'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[contains(@class, "product-brand-icon")]/img/@alt').string()

    sku = data.xpath('//div[@class="product-sku"]/span/text()').string()
    if not sku:
        sku = data.xpath('//select[@name="itemId"]/option/@value').string()
    if not sku:
        sku = data.xpath('//input[@name="itemId"]/@value').string()
    if sku:
        product.sku = sku.split()[-1]

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//li[@class="rating-container"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="rating-meta-date"]/text()').string()

        author = rev.xpath('.//span[@class="rating-meta-name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span/@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.split()[-1].replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//div[@class="rating-content"]//text()').string(multiple=True)
        if excerpt and len(excerpt) > 2:
            if 'Fazit:' in excerpt:
                excerpt, conclusion = excerpt.split('Fazit:')
                review.add_property(type='conclusion', value=conclusion)

            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[contains(@class, "load-more-button-ajax")]/@data-ajax-url').string()
    if next_url:
        session.queue(Request('https://www.dehner.de' + next_url), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
