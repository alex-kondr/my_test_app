from agent import *
from models.products import *


XCAT = ['NEW YEAR DEALS']


def run(context, session):
    session.queue(Request('https://www.createautomation.co.uk'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[@class=""]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name.title()))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//ul[@class="columns-3"]//a')
    for sub_cat in sub_cats:
        name = sub_cat.xpath('span[@class="name"]/text()').string()
        url = sub_cat.xpath('@href').string().replace('.html', '-1-14.html')
        session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-detail-holder"]')
    for prod in prods:
        name = prod.xpath('.//a/text()').string()
        url = prod.xpath('.//a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="reviews-count"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//a[contains(., "Next Page")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@id="catalogid"]/@value').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@itemprop="brand"]/@content').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs = data.xpath('//div[contains(@class, "user_reviews")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//em[@class="reviewed-by"]/text()').string(multiple=True)
        if date:
            review.date = date.split(' on ')[-1]

        author = rev.xpath('.//span[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        hlp_yes = data.xpath('.//span[@id="spnReview96"]//text()[contains(., "of")]').string()
        if hlp_yes:
            hlp_yes, hlp_cnt = hlp_yes.split('of')
            hlp_no = int(hlp_cnt) - int(hlp_yes)

            if int(hlp_yes) > 0:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

            if hlp_no > 0:
                review.add_property(type='not_helpful_votes', value=hlp_no)

        title = rev.xpath('.//div[@class="review-shortDesc"]/text()').string()
        excerpt = rev.xpath('.//div[@class="review-longDesc"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
