from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://iwantoneofthose.com/collections/board-games"), process_frontpage, dict(cat='Interests|Board Games'))
    session.queue(Request("https://iwantoneofthose.com/collections/trading-cards"), process_frontpage, dict(cat='Interests|Trading Cards'))
    session.queue(Request("https://iwantoneofthose.com/collections/collectables"), process_frontpage, dict(cat='Interests|Collectables'))
    session.queue(Request("https://iwantoneofthose.com/collections/nasa-gifts"), process_frontpage, dict(cat='Interests|NASA'))
    session.queue(Request("https://iwantoneofthose.com/collections/stranger-things-gifts"), process_frontpage, dict(cat='Interests|Stranger Things'))
    session.queue(Request("https://iwantoneofthose.com/collections/t-shirts"), process_frontpage, dict(cat='Clothing|Tees'))
    session.queue(Request("https://iwantoneofthose.com/collections/hoodies-and-sweatshirts"), process_frontpage, dict(cat='Clothing|Hoodies & Sweatshirts'))




def process_prodlist(data, context, session):
    prods = data.xpath('//li[@class="productListProducts_product"][.//span[@class="productBlock_reviewCount"]]')
    for prod in prods:
        name = prod.xpath('.//h3[@class="productBlock_productName"]/text()').string().strip()
        url = prod.xpath('.//a[@class="productBlock_link"]/@href').string()

        revs_cnt = prod.xpath('.//span[@class="productBlock_reviewCount"]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//button[@data-direction='next']")
    if next_page:
        next_page = context.get('page', 1) + 1
        next_url = data.xpath('//a[@data-page-number="{}"]/@href'.format(next_page)).string()
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].strip('| ').replace('||', '|')
    product.manufacturer = data.xpath('//div[@class="manchesterProductPage_actions"]//@data-product-brand').string()
    product.ssid = data.xpath('//div[@class="manchesterProductPage_actions"]//@data-product-id').string()
    product.sku = product.ssid

    mpn = data.xpath('''//script[contains(., '"mpn"')]/text()''').string()
    if mpn:
        mpn = mpn.split('"mpn":"')[-1].split('"')[0]
        product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs_url = data.xpath('//a[@class="productReviews_seeReviewsButton"]/@href').string()
    if revs_url:
        session.do(Request(revs_url), process_reviews, dict(product=product))
    else:
        context['product'] = product
        process_reviews(data, context, session)

    if product.reviews:
        session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="productReviews_review"]')
    if not revs:
        revs = data.xpath('//div[@class="productReviews_topReviewSingle"]')

    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = "user"

        review.title = rev.xpath('h3[@class="productReviews_reviewTitle"]//text()').string()
        if not review.title:
            review.title = rev.xpath('.//h3[@class="productReviews_topReviewTitle"]/text()').string()

        date = rev.xpath('.//span[@data-js-element="createdDate"]/text()').string()
        if date:
            date = date.split('/')
            review.date = '-'.join(date[::-1])

        author = rev.xpath('.//div[@class="productReviews_footerDateAndName"]//span[not(.//@data-js-element="createdDate")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        is_verified = rev.xpath('.//div[@class="productReviews_footerVerified"]')
        if is_verified:
            review.add_property(type="is_verified_buyer", value=True)

        hlp_yes = rev.xpath('.//a[@class="productReviews_voteYes"]/text()[contains(., "Yes")]').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes.split('(')[-1].strip(') '))
            if hlp_yes > 0:
                review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.xpath('.//a[@class="productReviews_voteNo"]/text()[contains(., "No")]').string()
        if hlp_no:
            hlp_no = int(hlp_no.split('(')[-1].strip(') '))
            if hlp_no > 0:
                review.add_property(type='not_helpful_votes', value=hlp_no)

        grade_overall = rev.xpath('.//span[@class="productReviews_schemaRatingValue"]/text()').string()
        if not grade_overall:
            grade_overall = rev.xpath('.//div[@class="productReviews_topReviewsRatingStarsContainer"]/@aria-label').string()
        if grade_overall:
            value = float(grade_overall.split(' Star')[0])
            review.grades.append(Grade(type="overall", value=value, best=5.0))

        excerpt = rev.xpath('.//p[@class="productReviews_reviewContent"]//text()').string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('.//p[@class="productReviews_topReviewsExcerpt"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt.strip())

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_reviews, dict(product=product))
