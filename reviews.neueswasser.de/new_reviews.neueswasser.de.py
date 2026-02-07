from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.neueswasser.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('(//li[contains(@class, "nav-item") and a[contains(., "Shop")]])[1]/ul[1]/li/a')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        
        print 'cat=', name
        session.queue(Request(url), process_category, dict(cat=name))


def process_category(data, context, session):
    subcats = data.xpath('//div[.//a[contains(text(), "Zu den Produkten")]]')
    for subcat in subcats:
        subcat_name = subcat.xpath('.//h2//text()').string(multiple=True)
        url = subcat.xpath('.//a[contains(text(), "Zu den Produkten")]/@href').string()
        
        print context['cat']+'|'+subcat_name
        # session.queue(Request(url), process_prodlist, dict(cat=context['cat']+'|'+subcat_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//script[@type="application/json" and contains(., "feedbackCount")]')
    for prod in prods:
        prod_json = simplejson.loads(prod.xpath('text()').string())

        product = Product()
        product.name = prod_json.get('texts', {}).get('name1')
        product.ssid = str(prod_json.get('item', {}).get('id'))
        product.sku = str(prod_json.get('variation', {}).get('id'))
        product.url = 'https://www.neueswasser.de/' + prod_json.get('texts', {}).get('urlPath') + '_' + product.ssid + '_' + product.sku
        product.category = context['cat']

        manufacturer = prod_json.get('item', {}).get('manufacturer')
        if manufacturer:
            product.manufacturer = manufacturer.get('externalName')

        revs_cnt = prod_json.get('item', {}).get('feedbackCount')
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://www.neueswasser.de/rest/feedbacks/feedback/helper/feedbacklist/{}/1'.format(product.ssid)
            session.do(Request(revs_url), process_reviews, dict(product=product))

        else:
            return

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


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
        if not author:
            author = rev.get('sourceRelation', [{}])[0].get('sourceRelationLabel')

        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('feedbackRating', {}).get('rating', {}).get('ratingValue')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('feedbackComment', {}).get('comment', {}).get('message')
        if excerpt and len(excerpt.strip(' +-.')) > 2:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('\n', ' ').strip(' +-.')
            if len(excerpt) > 2:
                review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    last_page = revs_json.get('pagination', {}).get('lastPage')
    next_page = context.get('page', 1) + 1
    if next_page <= int(last_page):
        next_url = 'https://www.neueswasser.de/rest/feedbacks/feedback/helper/feedbacklist/{ssid}/{page}'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, page=next_page))

    elif product.reviews:
        session.emit(product)