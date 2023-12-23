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
                    url = sub_cat.xpath('preceding-sibling::a[1]/@href').string()

                    if 'View all' not in sub_name:
                        session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[@class='st-product-list__item']")
    for prod in prods:
        name = prod.xpath(".//a[contains(@class,'st-block-link__target')]/text()").string()
        url = prod.xpath(".//a[contains(@class,'st-block-link__target')]/@href").string()

        reviews = prod.xpath(".//span[@class='st-product-cell__rating-count']")
        if reviews:
            session.queue(Request(url), process_product, dict(context, url=url, name=name))

    next_url = data.xpath("//a[@class='st-pagination__next']/@href").string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, context)


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.url = context['url']
    product.ssid = context['url'].split("/")[-1].split(".html")[0].split("=")[-1]
    product.manufacturer = data.xpath('//p[contains(text(), "Visit the")]/a/text()').string()
    product.sku = data.xpath('//strong[contains(text(), "SKU")]/following-sibling::span[@class="st-product-info__detail"]/text()').string()

    ean = data.xpath('//strong[contains(text(), "EAN")]/following-sibling::span[@class="st-product-info__detail"]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

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

        author = rev.xpath(".//div[@class='st-review__username']/text()").string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath("count(.//span[contains(@class, 'st-star--full')])")
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        verified_buyer = rev.xpath(".//div[@class='st-review__badge']")
        if verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[@class="st-review__stats"]/text()').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes.split('found')[0])
            if hlp_yes > 0:
                review.add_property(type='helpful_votes', value=hlp_yes)

        excerpt = rev.xpath(".//div[@class='st-review__content']/text()").string(multiple=True)
        if excerpt:
            excerpt = excerpt.replace('&#65533;', "'").replace('&#128513;', '').replace('&#127775;', '').replace('&#128514;', '').replace('&#128077;', '').replace('&#128512;', '').replace('&#128076;', '').replace('&#128525;', '').replace('&#65039;', '').replace('&#10084;', '').replace('&#128079;', '').replace('&#128522;', '').replace('&#128267;', '').replace('&#127996;', '').replace('&#128591;', '')
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = rev.xpath("@data-review-id").string()
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
