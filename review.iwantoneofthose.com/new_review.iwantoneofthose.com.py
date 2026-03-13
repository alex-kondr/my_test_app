from agent import *
from models.products import *


XCAT = ["Popular", "Gifts For Him", "Gifts For Her", "Blog", 'Brand', 'Offers', 'By Type', 'Film, TV & Gaming', 'Gifts By Recipient', 'Gifts by Occasion', 'Greeting Cards']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://www.iwantoneofthose.com/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@class="main-nav"]/li')
    for cat in cats:
        name = cat.xpath("a/text()").string()

        if name not in XCAT:
            if 'Gifts' in name:
                name = ''

            cats1 = cat.xpath('div[contains(@class, "nav__child")]/ul/li[summary]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('div/a/text()').string()

                if cat1_name not in XCAT:
                    if 'Type' in cat1_name:
                        cat1_name = ''

                    subcats = cat1.xpath('div[contains(@class, "nav__grandchild")]/ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath("text()").string().replace('Gifts For', '').replace('Gifts for', '').replace('Gifts', '').strip()

                            url = subcat.xpath("@href").string()
                            if subcat_name and url:
                                
                                print name+'|'+cat1_name+'|'+subcat_name, url
                                # session.queue(Request(url), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                    else:
                        url = cat1.xpath('div/a/@href').string()
                        
                        print name+'|'+cat1_name, url


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
