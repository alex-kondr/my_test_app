from agent import *
from models.products import *
import simplejson


XCAT = ['Deals']


def run(context, session):
    session.queue(Request('https://www.dinotech.org/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="navDropdown0"]/li')
    for cat in cats:
        name = cat.xpath('a/text()').string(multiple=True)

        if name not in XCAT:
            sub_cats = cat.xpath('ul/li')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a/text()').string(multiple=True)

                sub_cats1 = sub_cat.xpath('ul/li/a')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('text()').string(multiple=True)
                        url = sub_cat1.xpath('@href').string()
                        session.queue(Request(url + '?sorting=item.feedbackDecimal_desc', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url + '?sorting=item.feedbackDecimal_desc', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//ul[contains(@class, "product-list")]/li')
    for prod in prods:
        name = prod.xpath('.//a[@class="small"]/span/text()').string()
        url = prod.xpath('.//a[@class="small"]/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "feedback-stars")]/span/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))
        else:
            return

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//single-item/@__item-id').string()
    product.sku = product.ssid
    product.category = context['cat'].replace('Kapp-/', 'Kapp- &')

    prod_json = data.xpath('''//script[contains(., '"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.manufacturer = prod_json.get('manufacturer', {}).get('name')


    revs_url = 'https://www.dinotech.org/rest/feedbacks/feedback/helper/feedbacklist/{}/1?feedbacksPerPage=10'.format(product.ssid)
    session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json.get('feedbacks', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('authorName')
        author_ssid = rev.get('sourceRelation', [{}])[0].get('feedbackRelationSourceId')
        if not author:
            author = rev.get('sourceRelation', [{}])[0].get('sourceRelationLabel')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('feedbackRating', {}).get('rating', {}).get('ratingValue')
        if grade_overall and int(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get('feedbackComment', {}).get('comment', {}).get('message')
        if excerpt:
            excerpt = excerpt.replace('\r', '').replace('\n', ' ').strip()
            if len(excerpt) > 1:
                review.add_property(type="excerpt", value=excerpt)

                product.reviews.append(review)

    is_last_page = revs_json.get('pagination', {}).get('isLastPage')
    if not is_last_page:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.dinotech.org/rest/feedbacks/feedback/helper/feedbacklist/{ssid}/{page}?feedbacksPerPage=10'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(page=next_page, product=product))

    elif product.reviews:
        session.emit(product)
