from agent import *
from models.products import *
import simplejson


XCAT = ['Customer Service', 'Top Brands', 'All PC Games', 'PC Pre-Orders', 'Preorders', 'Switch Pre-Orders']
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: datadome=3G4uYDP3ZtNkg~SG8oQsCnfbxT0RSPyi5mmlBirWZyujc~PJQaXVSTm~UD4Dok63UtyxZpnknLRnCFQEvPEnVcE145e4gKSDCBYn4GvG9sADaelKixOql_TtdiOmiwR_; ab=dcbc64d5-3a44-4e03-ae14-b30fc6dec238; K.ID=539133a7-ad66-4410-bb69-1a165c2696a3; csrftoken=qdn76ExiPKKv4Vy5pOCD3FQTeLSRcS7i; postcode=3000; suburb=Melbourne; store_code=ma; _dd_s=aid=37595a0e-9b16-4350-961d-f938904b6cb1&rum=2&id=b4269576-204a-4309-b757-887de59fe09e&created=1772055066605&expire=1772056026612; rl_anonymous_id=%22539133a7-ad66-4410-bb69-1a165c2696a3%22; rl_page_init_referrer=%22%24direct%22; rl_session=%7B%22id%22%3A1772055067108%2C%22expiresAt%22%3A1772056897972%2C%22timeout%22%3A1800000%2C%22autoTrack%22%3Atrue%2C%22sessionStart%22%3Afalse%7D' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.mightyape.com.au/ma/', use='curl', force_charset='utf-8', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)
    
    print data.content

    cats = data.xpath('//nav[contains(@class, "surface-primary p")]')#/button/span[@class="grow"]')
    
    cats.pretty()
    for cat in cats:
        name = cat.xpath('text()').string()
        
        print 'name=', name

        cats1 = data.xpath('//section[contains(@class, "surface-primary px") and div/span[contains(text(), {})]]//div[h4]'.format(name))
        for cat1 in cats1:
            cat1_name = cat1.xpath('h4/a/text()').string()

            subcats = cat1.xpath('ul/li/a')
            for subcat in subcats:
                subcat_name = subcat.xpath('text()').string()
                url = subcat.xpath('@href').string()
                
                print name+'|'+cat1_name+'|'+subcat_name, url

        # if name1:
        #     cats1 = cat.xpath('.//div[contains(@class, "mega-sub-link")]')
        #     for cat2 in cats1:
        #         name2 = cat2.xpath('a/span/text()').string()

        #         if name2 and name2 not in XCAT:
        #             subcats = cat2.xpath('ul/li/a')
        #             for subcat in subcats:
        #                 name3 = subcat.xpath('text()').string()
        #                 url = subcat.xpath('@href').string()

        #                 if url and name3 and name3 not in XCAT:
        #                     name3 = name3.replace('Other ', '').replace('All ', '')
        #                     session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name1+'|'+name2+'|'+name3))


def process_prodlist(data, context, session):
    prods = data.xpath('//a[contains(@class, "product-item-title")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        if name and url:
            url = 'https://gorillagaming.com.au/products/' + url.split('/')[-1]
            session.queue(Request(url, use='curl'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat']
    product.ssid = data.xpath('//div[@class="rating-inner"]/div/@data-id').string()

    try:
        prod_json = simplejson.loads(data.xpath('''//script[@type="application/ld+json"][contains(., '"@type": "Product"')]//text()''').string().replace('.\ ', ' ').strip())

        product.manufacturer = prod_json.get('brand', {}).get('name')

        sku = prod_json.get('sku')

        ean = prod_json.get('gtin12')
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=ean))

        mpn = prod_json.get('mpn')
        if mpn:
            product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

        revs_cnt = prod_json.get('aggregateRating', {}).get('reviewCount')
        if revs_cnt and int(revs_cnt) > 0 and product.ssid:
            revs_url = 'https://judge.me/reviews/reviews_for_widget?url=gorilla-gaming-au.myshopify.com&shop_domain=gorilla-gaming-au.myshopify.com&platform=shopify&page=1&per_page=10&product_id=' + product.ssid
            session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(product=product, ssid=product.ssid))
    except:
        return


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    new_data = data.parse_fragment(revs_json['html'])

    revs = new_data.xpath("//div[@class='jdgm-rev jdgm-divider-top']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//b[@class='jdgm-rev__title']//text()").string()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath("@data-review-id").string()

        date = rev.xpath(".//span[@class='jdgm-rev__timestamp jdgm-spinner']/@data-content").string()
        if date:
            review.date = date.split()[0]

        author = rev.xpath(".//span[@class='jdgm-rev__author']/text()").string()
        if author and author != 'null':
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath(".//span[@data-score]/@data-score").string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('@data-verified-buyer').string()
        if is_verified == 'true':
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('@data-thumb-up-count').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('@data-thumb-down-count').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        excerpt = rev.xpath(".//div[@class='jdgm-rev__body']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            product.reviews.append(review)

    next_url = new_data.xpath('//a[@rel="next"]/@data-page').string()
    if next_url:
        next_page = context.get("page", 1) + 1
        revs_url = 'https://judge.me/reviews/reviews_for_widget?url=gorilla-gaming-au.myshopify.com&shop_domain=gorilla-gaming-au.myshopify.com&platform=shopify&page=' + str(next_page) + '&per_page=10&product_id=' + context['ssid']
        session.do(Request(revs_url, use='curl', force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, page=next_page))
    elif product.reviews:
        session.emit(product)