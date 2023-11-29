from agent import *
from models.products import *
import simplejson


XCATS = ['Fan Shop']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.scheels.com/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="has-children tier-1"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        sub_cats = cat.xpath('ul/li[@class="tier-2 has-children"]')
        if name not in XCATS:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string()

                sub_cats1 = sub_cat.xpath('ul/li[@class="has-children third-level tier-3"]')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('a//text()').string()

                        sub_cats2 = sub_cat1.xpath('ul/li[@class="tier-4"]/a')
                        if sub_cats2:
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.xpath('text()').string()
                                url = sub_cat2.xpath('@href').string()
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                        else:
                            url = sub_cat1.xpath('a/@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-tile"]')
    for prod in prods:
        product = Product()
        product.category = context['cat']
        product.name = prod.xpath('@data-itemname').string()
        product.ssid = prod.xpath('@data-uuid').string()
        product.sku = prod.xpath('@data-itemid').string()
        product.url = prod.xpath('.//div[@class="product-image"]//a/@href').string()

        revs_cnt = prod.xpath('(following::div[@class="TTteaser"])[1]/@data-reviewcount').string()
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = 'https://cdn-ws.turnto.com/v5/sitedata/TXOE2FrZzlhkSdesite/{}/d/review/en_US/0/9999/%7B%7D/RECENT/false/false/'.format(product.sku)
            session.queue(Request(revs_url), process_reviews, dict(product=product))

    next_url = data.xpath('//a[@class="page-next button is-primary"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('reviews', [])
    for rev in revs:
        review = Review()
        review.url = product.url
        review.type = 'user'
        review.title = rev.get('title')
        review.date = rev.get('dateCreatedFormatted')

        first_name = rev.get('user', {}).get('firstName')
        last_name = rev.get('user', {}).get('lastName')
        author = '{first_name} {last_name}'.format(first_name=first_name, last_name=last_name).replace('None', '').strip()
        if not author:
            author = rev.get('user', {}).get('nickName')

        author_ssid = rev.get('user', {}).get('id')
        if not author_ssid:
            author_ssid = author

        if author:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))

        is_verified = rev.get('purchaseDateFormatted')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.get('recommended')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.get('upVotes')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.get('downVotes')
        if hlp_no and hlp_no > 0:
            review.add_property(type='not_helpful_votes', value=hlp_no)

        grade_overall = rev.get('rating')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('text')
        if excerpt:
            excerpt = excerpt.replace('<br />', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            ssid = rev.get('id')
            if ssid:
                review.ssid = str(ssid)
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # no next page
