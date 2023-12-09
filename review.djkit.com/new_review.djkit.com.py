from agent import *
from models.products import *


XCAT = ['Top Brands', 'Best Sellers', 'Shop by Brand', 'To Brands', 'Best sellers', 'Sale items']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://www.djkit.com"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="st-category-guide__category-container"]/div[@class="st-category-guide__list"]')
    for cat in cats:
        for i in range(int(cat.xpath('count(div[@class="st-menu-header"])'))):
            name = cat.xpath('div[@class="st-menu-header" and count(preceding-sibling::hr[@class="st-menu-separator"])={i}]//text()'.format(i=i)).string(multiple=True)

            if name not in XCAT and 'Top 10' not in name:
                sub_cats = cat.xpath('div[@class="st-menu-item__title" and count(preceding-sibling::hr[@class="st-menu-separator"])={i}]'.format(i=i))
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('text()').string()

                    cat = name if 'View all' in sub_name else name + '|' + sub_name

                    url = sub_cat.xpath('preceding-sibling::a[1]/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=cat))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='st-product-list__item']")
    for prod in prods:
        name = prod.xpath(".//a[contains(@class,'st-block-link__target')]/text()").string()
        url = prod.xpath(".//a[contains(@class,'st-block-link__target')]/@href").string()

        reviews = prod.xpath(".//span[@class='st-product-cell__rating-count']")
        if reviews:
            session.queue(Request(url, use='curl'), process_product, dict(context, url=url, name=name))

    next_url = data.xpath("//a[@class='st-pagination__next']/@href").string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_prodlist, context)


def process_product(data, context, session):##############
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']

    sku_id = data.xpath("//p[contains(@class, 'st-product-info ')]//span[1]/text()").string()
    ean_id = data.xpath("//p[contains(@class, 'st-product-info ')]//span[last()]/text()").string()
    if ean_id == sku_id:
        ean_id = None
    if sku_id:
        product.sku = sku_id
    if ean_id:
        product.add_property(type='id.ean', value=ean_id)

    if sku_id or ean_id:
        product.ssid = sku_id or ean_id
    else:
        product.ssid = context['url'].split("/")[-1].split(".html")[0]

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath("//div[@class='st-review' or @class='st-review hide']")
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev.xpath(".//div[@class='st-review__title']/text()").string()
        review.url = product.url
        review.date = rev.xpath(".//div[@class='st-review__date']/text()").string()
        review.ssid = rev.xpath("@data-review-id").string()

        author_name = rev.xpath(".//div[@class='st-review__username']/text()").string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        verified_buyer = rev.xpath(".//div[@class='st-review__badge']")
        if verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        grade_overall = rev.xpath("count(.//span[contains(@class, 'st-star--full')])")
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.xpath(".//div[@class='st-review__content']/text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)
