from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.jardins-loisirs.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@data-depth="0"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True)

        sub_cats = cat.xpath('.//ul[@data-depth="1"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a//text()').string(multiple=True)

            sub_cats1 = sub_cat.xpath('.//ul[@data-depth="2"]//a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('.//text()').string(multiple=True)
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))


def process_prodlist(data, context, session):
    prods = data.xpath('//h3[contains(@class, "product-title")]/a')
    for prod in prods:
        name = prod.xpath('text()').string().replace('...', '')
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//lin[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = data.xpath('//input/@data-id_product').string()
    product.sku = product.ssid
    product.manufacturer = data.xpath('//span[@class="manufacturer-logo"]//@alt').string()

    prod_json = data.xpath('//script[@type="application/ld+json" and contains(., '"mpn"')]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        mpn = prod_json.get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//dl[contains(., "EAN-13")]/dd[contains(@class, "value")]/text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs_url = 'https://www.jardins-loisirs.com/module/productcomments/ListComments?id_product={sku}'.format(sku=product.sku)
    session.do(Request(revs_url), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)

    revs = revs_json.get('comments')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id_product_comment'))

        date = rev.get('date_add')
        if date:
            review.date = date.split()[0]

        author = rev.get('customer_name')
        if author:
            author = author.replace('&egrave;', 'è').replace('&eacute;', 'é').replace('&ecirc;', 'ê').replace('&ccedil;', 'ç').replace('&ccedil;', 'ç').replace('&agrave;', 'à').replace('&acirc;', 'â').replace('&ocirc;', 'ô').replace('&times;', '').replace('&quot;', '"').replace('&#039;', "'").replace('&amp;', '&').replace('&rsquo;', '’').replace('&sup2;', '²').replace('\r\n', ' ').replace("''", "'").replace('  ', ' ').replace('&icirc;', 'î').replace('&Ccedil;', 'Ç').replace('&ucirc;', 'û').replace('&ugrave;', 'ù').replace('&hellip;', '').strip()
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('grade')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        helpful = rev.get('usefulness')
        if helpful:
            review.add_property(type='helpful_votes', value=helpful)

        not_helpful = rev.get('total_usefulness') - helpful
        if not_helpful:
            review.add_property(type='not_helpful_votes', value=not_helpful)

        title = rev.get('title')
        excerpt = rev.get('content')
        if excerpt and title:
            review.title = title.replace('&egrave;', 'è').replace('&eacute;', 'é').replace('&ecirc;', 'ê').replace('&ccedil;', 'ç').replace('&ccedil;', 'ç').replace('&agrave;', 'à').replace('&acirc;', 'â').replace('&ocirc;', 'ô').replace('&times;', '').replace('&quot;', '"').replace('&#039;', "'").replace('&amp;', '&').replace('&rsquo;', '’').replace('&sup2;', '²').replace('\r\n', ' ').replace("''", "'").replace('  ', ' ').replace('&icirc;', 'î').replace('&Ccedil;', 'Ç').replace('&ucirc;', 'û').replace('&ugrave;', 'ù').replace('&hellip;', '').strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.replace('&egrave;', 'è').replace('&eacute;', 'é').replace('&ecirc;', 'ê').replace('&ccedil;', 'ç').replace('&ccedil;', 'ç').replace('&agrave;', 'à').replace('&acirc;', 'â').replace('&ocirc;', 'ô').replace('&times;', '').replace('&quot;', '"').replace('&#039;', "'").replace('&amp;', '&').replace('&rsquo;', '’').replace('&sup2;', '²').replace('\r\n', ' ').replace("''", "'").replace('  ', ' ').replace('&icirc;', 'î').replace('&Ccedil;', 'Ç').replace('&ucirc;', 'û').replace('&ugrave;', 'ù').replace('&hellip;', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_cnt = revs_json.get('comments_nb')
    offset = context.get('offset', 0) + 5
    if revs_cnt and int(revs_cnt) > offset:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.jardins-loisirs.com/module/productcomments/ListComments?id_product={sku}&page={next_page}'.format(sku=product.sku, next_page=next_page)
        session.do(Request(next_url), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
