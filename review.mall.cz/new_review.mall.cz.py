from agent import *
from models.products import *
import simplejson
import re
import random
import time


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101 Firefox/160.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: _cmuid=3ff6b2d2-b315-4f62-86c9-40374c6c3c84; datadome=HEEmSdN5pOIdO4FNTI8vt0lKybu4mwRaAvbL5jA9PqLP0dryZvN3gOwMeFPVf_n0uE3RHdCjlNDleLTRWzQXVlNYY8XLCK77zlyu2DiFVBGazv_EeM~HS_DhJwvD5Vm2; OptOutOnRequest=groups=googleAnalytics:1,googleAdvertisingProducts:1,tikTok:1,allegroAdsNetwork:1,facebook:1,rtbHouse:1,rasp:1,pinterest:1; gdpr_permission_given=1; _meta_googleGtag_settings=4e5a45d52f17bc4e567bbe2aaafea8a73d012998; g_state={"i_l":3,"i_ll":1795000447616,"i_b":"zmarAOlREq/fROmCtS/IsCPYP4SZZqsJjCcSz6W/VNk","i_e":{"enable_itp_optimization":24},"i_et":1795000447616,"i_p":1795605137356}; _fbp=fb.1.1789565931481.792485742; _meta_facebookTag_sync=1789565931481; _ttp=J_wp3sxF7ofCYxC6fnsSVQ_vxAl; _meta_rtbHouse_settings=3dda4a52a350b6c1012f65a65e347d9115a6c925; wdctx=v5.hw5EMtdpVZ5aDifR8VgXYeIPh4uIpP0Ft_71KifNg1aaxqNQxu1lyl4vIcKKgWofFgXFg1wfuhs-_xXvisX9CA7Qcx9IN81qxlyyt0AiXxs0Up9VHDmUewElitMQAbVD4Fik2qJ1jy7LHuKuo50SZ-DiJ79UoaMmFNJFQWRViz_qYV_L-9EyoG1yb_wVMhdyhYDAzVLKq9a1ZhxDyvF0R5UwH11-qDq7KDK9uJ3-Y4z9.ZQ01KlHUTAGjjLSoezOiCQ.ulRF9V-lQVY; _meta_versions=v1|fc.23.3,ft.24.2,gt.26.2,ma.28.1,rh.25.1,tk.27.2,up.26.2; _meta_urlParameters_utm_source=mall.cz; _meta_urlParameters_utm_source_30=mall.cz; _meta_urlParameters_utm_source_30_timestamp=1795000447603; _meta_microsoftAds_mid=dcf10649-d527-43c3-90f8-3ca05bf4d1af; _meta_microsoftAds_beaconFired=1795000333071; _meta_googleGtag_ga_session_count=1; _meta_googleGtag_ga=GA1.2.603745711.1795000333; _meta_googleGtag_ga_library_loaded=1795000447609' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://allegro.cz/obchod/mall-cz?utm_source=mall.cz&dd_referrer=', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(2, 5))

    cats = data.xpath('//nav/a[contains(@id, "nav-item")]')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(2, 5))

    subcats = data.xpath('//div[contains(@id, "pageLinks")]//div[@class="root"]//a')
    if not subcats and not context.get('repeated'):
        subcats = data.xpath('//ul[@id="links-list-Categories"]/li//a')
        if not subcats:
            subcats = data.xpath('//div[@data-role="carousel"]//ul/li/a[.//p]')

    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for subcat in subcats:
        subcat_name = subcat.xpath('.//text()').string(multiple=True)

        url = subcat.xpath('@href').string().replace('order=qd', '').strip('?& ')
        if 'order=prd' not in url:
            if '?' in url:
                url = url + '&order=prd'
            else:
                url = url + '?order=prd'

        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_catlist, dict(cat=context['cat']+'|'+subcat_name, repeated=True))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(2, 5))

    prods = data.xpath('//li[article]//div[h2]')
    for prod in prods:
        name = prod.xpath('h2/a/text()').string()
        url = prod.xpath('h2/a/@href').string().split('?')[0]
        ssid = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', url)

        revs_cnt = prod.xpath('div/div/span[regexp:test(text(), "\(\d+\)")]/text()').string()
        
        print 'revs_cnt=', revs_cnt
        
        if revs_cnt and int(revs_cnt.strip('( )')) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_product, dict(context, name=name, url=url, ssid=ssid))
        else:
            return

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.sku = data.xpath('//button[@role="link"]/@data-analytics-interaction-value').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//a[@data-analytics-interaction-label="brandLink"]/text()').string()

    product.ssid = data.xpath('//a[contains(@href, "#inne-oferty-produktu")]/@data-analytics-click-value').string()
    if not product.ssid and context['ssid']:
        product.ssid = context['ssid'].group(0)

    try:
        prod_json = data.xpath('''//script[contains(., '"name":"Kód výrobce"')]/text()''').string()

        params = simplejson.loads(prod_json).get('facade', {}).get('parameters', [])
        for param in params:
            if param.get('name') == 'Kód výrobce':
                mpn = param.get('values', [{}])[0].get('valueLabel')
                if mpn:
                    product.add_property(type='id.manufacturer', value=mpn)
    except:
        pass

    try:
        prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()

        ean = simplejson.loads(prod_json).get('gtin')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type='id.ean', value=str(ean))
    except:
        pass

    if product.ssid:
        revs_url = 'https://edge.allegro.cz/product-reviews?productId=' + product.ssid
        session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = context['product']

    try:
        revs_json = simplejson.loads(data.content).get('reviews', {})
    except:
        revs_json = {}

    revs = revs_json.get('opinions', [])
    for rev in revs:
        if rev.get('sourceLanguage') != 'cs-CZ':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev['id']

        date = rev.get('createdAt')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('author', {}).get('name')
        if author:
            author = remove_emoji(author).strip()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade = rev.get('rating', {}).get('label')
        if grade and float(grade) > 0:
            review.grades.append(Grade(type='overall', value=float(grade), best=5.0))

        hlp_yes = rev.get('helpfulness', {}).get('positive', {}).get('count')
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.get('helpfulness', {}).get('negative', {}).get('count')
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        pros = rev.get('pros')
        if pros:
            pros = pros.strip(' +-*.:;•,–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

        cons = rev.get('cons')
        if cons:
            cons = cons.strip(' +-*.:;•,–')
            if len(cons) > 1:
                review.add_property(type='cons', value=cons)

        excerpt = rev.get('opinion')
        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = context.get('revs_cnt', revs_json.get('count', 0))
    offset = context.get('offset', 0) + 15
    if offset < revs_cnt:
        next_page = context.get('page', 1) + 1
        revs_url = 'https://edge.allegro.cz/product-reviews?productId=' + product.ssid + '&page=' + str(next_page)
        session.do(Request(revs_url, force_charset='utf-8', max_age=0), process_reviews, dict(product=product, offset=offset, page=next_page, revs_cnt=revs_cnt))

    elif product.reviews:
        session.emit(product)