from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.whiteaway.se/'), process_fronpage, dict())


def process_fronpage(data, context, session):
    cats = data.xpath('//div[@class="sc-59c922c8-0 logaWd"]')
    for cat in cats:
        name = cat.xpath('span/span/text()').string()

        sub_cats = cat.xpath('.//div[@class="sc-1eca6fc5-0 JbAtb"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('.//span[@class="sc-75c11d93-0 ivNzjP"]/text()').string()

            sub_cats1 = sub_cat.xpath('a[@class="sc-1f701fb5-0 dPJNaz"]')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('span/text()').string()
                url = sub_cat1.xpath('@href').string()

                if 'Erbjudanden' not in sub_name1:
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods_json = data.xpath('//script[contains(., "listing")]/text()').string()
    if prods_json:
        prods = simplejson.loads(prods_json.replace('var vueData = ', '').strip(';')).get('listing', [])

        for prod in prods:
            product = Product()
            product.name = prod.get('_1')
            product.url = 'https://www.whiteaway.se/' + prod.get('_3')
            product.ssid = prod.get('_29')
            product.category = context['cat']
            product.manifacturer = prod.get('_7')

            mpn = prod.get('_6')
            revs_cnt = prod.get('_5')
            if mpn and revs_cnt and int(revs_cnt) > 0:
                product.add_property(type='id_manufacturer', value=mpn)

                url = 'https://api.bazaarvoice.com/data/batch.json?passkey=lwlek4awxjzijgl7q77uroukt&apiversion=5.5&displaycode=13336-sv_se&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A{}&filter.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&sort.q0=relevancy%3Aa1&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&filter_reviewcomments.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&filter_comments.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&limit.q0=100&offset.q0=0&limit_comments.q0=1'.format(mpn)
                session.queue(Request(url), process_reviews, dict(product=product, mpn=mpn))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content).get('BatchedResults', {}).get('q0', {})

    revs = revs_json.get('Results', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.get('SubmissionTime')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('UserNickname')
        author_ssid = rev.get('AuthorId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('Rating')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_recommended = rev.get('IsRecommended')
        if is_recommended and is_recommended == True:
            review.add_property(type='is_recommended', value=True)

        title = rev.get('Title')
        excerpt = rev.get('ReviewText')
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_prperty(type='excerpt', value=excerpt)

            review.ssid = rev.get('Id')
            if not review.ssid:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('TotalResults', 0)
    offset = context.get('offset', 0) + 100
    if offset < revs_cnt:
        url = 'https://api.bazaarvoice.com/data/batch.json?passkey=lwlek4awxjzijgl7q77uroukt&apiversion=5.5&displaycode=13336-sv_se&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A{mpn}&filter.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&sort.q0=relevancy%3Aa1&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&filter_reviewcomments.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&filter_comments.q0=contentlocale%3Aeq%3Ada_DK%2Cno_NO%2Csv_SE&limit.q0=100&offset.q0={offset}&limit_comments.q0=1'.format(mpn=context['mpn'], offset=offset)
        session.queue(Request(url), process_reviews, dict(product=product, offset=offset))

    elif product.review:
        session.emit(product)
