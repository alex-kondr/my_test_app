from agent import *
from models.products import *


XCAT = ['Ink Cartridges', 'Paper & Notebooks', 'Softwares', 'Gifts & Combos', 'Wires & Cables', 'Wire & Cable Accessories', 'Paints & Coatings', 'USB Data Cables', 'Mobile Cases & Covers', 'Mobile Screen Guards', 'Aux Cables', 'Mobile Camera Protectors', 'Network Cables', 'Services']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.moglix.com/all-categories', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="all-cate-section pad-15"]')
    for cat in cats:
        name = cat.xpath('h3[@class="red-txt"]/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('.//div[@class="cate-type"]')
            if sub_cats:
                for sub_cat in sub_cats:
                    sub_name = sub_cat.xpath('.//strong[@*[contains(name(), "data-_ngcontent-sc")]]/text()').string()

                    if sub_name not in XCAT:
                        sub_cats1 = sub_cat.xpath('a[not(strong)]')
                        if sub_cats1:
                            for sub_cat1 in sub_cats1:
                                sub_name1 = sub_cat1.xpath('text()').string()
                                url = sub_cat1.xpath('@href').string()

                                if sub_name1 not in XCAT:
                                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))

                        else:
                            url = sub_cat.xpath('a[strong]/@href').string()
                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[div[@class="brand"]]')
    for prod in prods:
        name = prod.xpath('div[@class="name"]//span/text()').string()
        manufacturer = prod.xpath('div[contains(@class, "brand")]/span/text()').string().replace('By:', '').strip().title()
        url = prod.xpath('div[@class="name"]/a/@href').string()

        revs = prod.xpath('.//span[starts-with(@class, "count")]/text()')
        if revs:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].upper()
    product.sku = product.ssid
    product.category = context['cat'].replace('Other ', '')
    product.manufacturer = context['manufacturer']

    revs_url = product.url.replace('https://www.moglix.com/', 'https://www.moglix.com/product-reviews/')
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="reviewRow"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//p[contains(@class, "date")]/text()').string()

        author = rev.xpath('.//p[@class="customer-name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//i[contains(@class, "green-txt")])')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        is_verified = rev.xpath('.//p[contains(., "Verified Buyer")]')
        if is_verified:
            review.add_property(type="is_verified_buyer", value=True)

        helpful = rev.xpath('.//button[i[contains(@class, "icon-like")]]/span/text()').string()
        if helpful and helpful.isdigit() and int(helpful) > 0:
            review.add_property(type='helpful_votes', value=int(helpful))

        not_helpful = rev.xpath('.//button[i[contains(@class, "icon-dislike ")]]/span/text()').string()
        if not_helpful and not_helpful.isdigit() and int(not_helpful) > 0:
            review.add_property(type='not_helpful_votes', value=int(not_helpful))

        title = rev.xpath('.//p[contains(@class, "heading")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@class="content"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# not next page
