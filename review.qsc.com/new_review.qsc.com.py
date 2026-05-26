from agent import *
from models.products import *


XCAT = ['Solutions', 'Software & Firmware']


def run(context, session):
    session.queue(Request('https://www.qsc.com/products/', use='curl', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="container container-full"]')
    for cat in cats:
        name = cat.xpath('div/h2/text()').string()

        if name and name.title() not in XCAT:
            cats1 = cat.xpath('.//div[@data-column]/div[@data-button-dropdown]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('button/text()').string().title()

                cats2 = cat1.xpath('.//div[@class="csc-typography"]')
                for cat2 in cats2:
                    cat2_name1 = cat2.xpath('.//p[@class="bodytext"]//span[contains(@style, "20px")]//a/text()').string()

                    subcats = cat2.xpath('.//p[@class="bodytext"]//span[not(contains(@style, "20px"))]//a|.//ul//a')
                    for subcat in subcats:
                        prod_name = subcat.xpath('.//text()').string(multiple=True)
                        url = subcat.xpath('@href').string()
                        cat = name.title() + '|' + cat1_name + ('|' + cat2_name1.title() if cat2_name1 and cat2_name1 != cat1_name else '')
                        session.queue(Request(url, use='curl', max_age=0), process_product, dict(cat=cat, name=prod_name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = context['cat']
    product.manufacturer = 'QCS'

    revs_url = data.xpath('//a[contains(., "Reviews")]/@href').string()
    if revs_url:
        session.queue(Request(revs_url.replace('.qsc.', '.qscaudio.'), use='curl', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="qscreview"]/div[@class="row"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.xpath('.//h3/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//i[@class="onestar"]) + count(.//i[@class="halfstar"]) * 0.5')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        title = rev.xpath('.//h4//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="ten-tablet"]//p//text()').string(multiple=True)
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