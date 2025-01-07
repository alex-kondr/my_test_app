from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://community.spiceworks.com/tag/product-reviews/l/latest.json?page=0&tags[]=product-reviews', force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods_json = simplejson.loads(data.content).get('topic_list', {})

    prods = prods_json.get('topics', [])
    for prod in prods:
        product = Product()
        product.name = prod.get('title')
        product.ssid = str(prod.get('id'))
        product.url = 'https://community.spiceworks.com/t/' + prod.get('slug') + '/' + product.ssid
        product.category = '|'.join([tag.replace('-', ' ').title() for tag in prod.get('tags', []) if 'review' not in tag])

        revs_cnt = prod.get('posts_count', 0)
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(product.url), process_reviews, dict(product=product))

    next_url = prods_json.get('more_topics_url')
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict())


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@itemprop="comment"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.title = rev.xpath('.//h3//text()').string(multiple=True)
        review.url = product.url

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//span[@itemprop="name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//p[contains(., "stars") and contains(., "out of")]/text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.split()[0])
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        pros = rev.xpath('.//h4[contains(., "pros")]/following-sibling::p[preceding-sibling::h4[1][contains(., "pros")]]')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = rev.xpath('.//h4[contains(., "cons")]/following-sibling::p[preceding-sibling::h4[1][contains(., "cons")]]')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        excerpt = rev.xpath('.//h4[contains(., "pros")]/preceding-sibling::p//text()').string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('.//h4[contains(., "cons")]/preceding-sibling::p//text()').string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('.//h4[contains(., "Rating")]/preceding-sibling::p//text()').string(multiple=True)

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if revs:
        rev_numb = context.get('rev_numb', 20) + 1
        next_url = product.url + '/{}'.format(rev_numb)
        session.do(Request(next_url), process_reviews, dict(product=product, rev_numb=rev_numb))

    elif product.reviews:
        session.emit(product)
