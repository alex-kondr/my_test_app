#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
import simplejson


XCAT = ["Golden Friday", "SALE", "Gifts", "Brands", "UAE", "Top Brands", "Offers", "Explore", "View All", "Top Picks"]


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    meta_re = re.compile('<ul class="filter-available".*?</ul>', re.DOTALL)
    incontent = file(data.content_file).read()
    outcontent = meta_re.sub("", incontent)
    outcontent = outcontent.replace(' xmlns=', ' abcd=')
    outcontent = outcontent.replace(' xmlns:', ' abcd:')
    outcontent = outcontent.replace('ns0:', '')
    outcontent = outcontent.replace('<!-------', '<!--')
    outcontent = outcontent.replace('----->', '-->')
    # print len(incontent), len(outcontent)
    file(tmp, "w").write(outcontent)
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.jashanmal.com'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="nav-bar__linklist list--unstyled"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[contains(@class, "mega-menu__inner ")]/div')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a//text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('ul/li/a')

                    for subcat in subcats:
                        url = subcat.xpath('@href').string()
                        subcat_name = subcat.xpath('text()').string()

                        if subcat_name not in XCAT:
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods_json = data.xpath('''//script[contains(., '"collection_viewed", ')]//text()''').string()
    if not prods_json:
        return

    prods_json = simplejson.loads(prods_json.split('"collection_viewed", ')[-1].split(');},"https://www.jashanmal.com/cdn"')[0])

    prods = prods_json.get('collection', {}).get('productVariants', [])
    for prod in prods:
        name = prod.get('product', {}).get('title')
        url = 'https://www.jashanmal.com' + prod.get('product', {}).get('url', '').replace('\/', '/')
        ssid = prod.get('product', {}).get('id')
        brand = prod.get('product', {}).get('vendor')
        mpn = prod.get('sku')
        session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid, brand=brand, mpn=mpn))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['category'] = context['cat']
    pr['url'] = context['url']
    pr['manufacturer'] = context.get('brand')

    pr['mpn'] = context.get('mpn')
    pr['ssid'] = context.get('ssid')

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['ean'] = prod_json.get('offers', [{}])[0].get('gtin13')
    except:
        pass

    if pr['ssid'] and not session.seen(pr['ssid']):
        context['product'] = pr
        context['apiKey'] = 'pubkey-OX50u46uD98Z57TYHq0amWyKh04j7J'
        context['storeUrl'] = 'www.jashanmal.com'
        process_reviews_stamped(data: Response, context: dict[str, str], session: Session)


def process_reviews_stamped(data: Response, context: dict[str, str], session: Session):
    if not context.get('stampedPage'):
        if context['product'].get('ssid') and context.get('apiKey') and context.get('storeUrl'):
            revs_url = 'https://stamped.io/api/widget?productId=' + str(context['product'].get('ssid')) + '&page=1&apiKey=' + str(context['apiKey']) + '&storeUrl=' + str(context['storeUrl']) + '&take=10'
            session.queue(Request(revs_url), process_reviews_stamped, dict(context, stampedPage=1))
            return

    if not context.get('product'):
        print('No product in context')
        return

    product = Product()
    product.name = context['product'].get('name')
    product.ssid = context['product'].get('ssid')
    product.category = context['product'].get('category')
    product.url = context['product'].get('url')
    product.manufacturer = context['product'].get('manufacturer')

    if context['product'].get('ean'):
        product.properties.append(ProductProperty(type='id.ean', value=context['product'].get('ean')))

    if context['product'].get('mpn'):
        product.properties.append(ProductProperty(type='id.manufacturer', value=context['product'].get('mpn')))

    resp = simplejson.loads(data.content)
    revs_amount = resp['count']

    if (context.get('debug', 0) == 1):
        if revs_amount == 0:
            print("No reviews for " + product.name)
            return
        else:
            print("There are " + str(revs_amount) + " reviews for " + product.name)

    if revs_amount == 0:
        return

    revs_html = resp['widget']
    revs_block = data.parse_fragment(revs_html)

    revs = revs_block.xpath("//div[@class='stamped-review']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//div[@class='stamped-review-header-title']//text()").string()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath(".//div[@class='created']//text()").string()
        review.ssid = rev.xpath("@id").string().split('-')[-1]

        author_name = rev.xpath(".//strong[@class='author']//text()").string()
        review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath("@data-rating").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        if not grade_overall:
            grade_overall = len(rev.xpath(".//i[@class='stamped-fa stamped-fa-star']"))
            if grade_overall > 0:
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_verified = rev.xpath("@data-verified").string()
        if is_verified and is_verified == "buyer":
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath(".//p[@class='stamped-review-content-body']//text()").string(multiple=True)
        if excerpt:
            if (context.get('debug', 0) == 1):
                print(excerpt)

            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 10
    if offset < revs_amount:
        stampedPage = context['stampedPage'] + 1
        revs_url = 'https://stamped.io/api/widget?productId=' + str(context['product'].get('ssid')) + '&page=' + str(stampedPage) + '&apiKey=' + str(context['apiKey']) + '&storeUrl=' + str(context['storeUrl']) + '&take=10'
        session.queue(Request(revs_url), process_reviews_stamped, dict(context, stampedPage=stampedPage, offset=offset))
