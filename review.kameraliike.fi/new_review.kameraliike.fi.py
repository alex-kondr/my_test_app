from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.kameraliike.fi'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats_json = data.xpath('//div/@data-page').string()
    if not cats_json:
        return

    cats = simplejson.loads(cats_json).get('props', {}).get('menus', {}).get('mainmenu1', [{}])[0].get('children', [])
    for cat in cats:
        name = cat.get('name')

        sub_cats = cat.get('children')
        if sub_cats:
            for sub_cat in sub_cats:
                sub_name = sub_cat.get('name')

                sub_cats1 = sub_cat.get('children')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.get('name')

                        sub_cats2 = sub_cat1.get('children')
                        if sub_cats2:
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.get('name')
                                url = sub_cat2.get('link')
                                session.queue(Request('https://www.kameraliike.fi' + url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                        else:
                            url = sub_cat1.get('link')
                            session.queue(Request('https://www.kameraliike.fi' + url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.get('link')
                    session.queue(Request('https://www.kameraliike.fi' + url), process_prodlist, dict(cat=name + '|' + sub_name))
        else:
            url = cat.get('link')
            session.queue(Request('https://www.kameraliike.fi' + url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods_json = data.xpath('//div/@data-page').string()
    if not prods_json:
        return

    prods_json = simplejson.loads(prods_json).get('props', {}).get('products', {})

    prods = prods_json.get('data', [])
    for prod in prods:
        ssid = prod.get('id')
        name = prod.get('name')
        url = prod.get('link')

        revs_cnt = prod.get('reviews', {}).get('totalCount', 0)
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, ssid=ssid, url=url))

    next_page = context.get('page', 1) + 1
    last_page = prods_json.get('pagination', {}).get('lastPage', 1)
    if int(next_page) <= int(last_page):
        next_url = data.response_url.split('?page=')[0] + '?page=' + str(next_page)
        session.queue(Request(next_url), process_prodlist, dict(context, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = product.url.split('/')[-1]
    product.category = context['cat']

    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        if prod_json:
            product.manufacturer = prod_json[0].get('brand', {}).get('name')

            mpn = prod_json[0].get('mpn')
            if mpn:
                product.add_property(type='id.manufacturer', value=mpn)

            ean = prod_json[0].get('gtin')
            if ean and len(ean) > 10:
                product.add_property(type='id.ean', value=str(ean))

    revs = data.xpath('//div[contains(@class, "flex flex-col space-y-2.5")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//span[@class="text-base"]/text()').string()

        author = rev.xpath('.//h4[contains(@class, "text-left")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//svg[contains(@class, "fill-[#FDB300]")]) + count(.//svg[contains(@class, "w-9 h-9")]) div 2')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//div[contains(@class, "line-clamp-4 text-base")]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip(' +-.:;\n\t')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
