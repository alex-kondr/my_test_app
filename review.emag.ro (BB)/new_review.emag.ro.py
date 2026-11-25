#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *


XCAT = ['Contul meu', 'Branduri de TOP', 'Resigilate', 'Alege produsul potrivit:', 'Servicii Instalare - Montaj', 'Branduri de TOP:', 'Laptopuri Resigilate', 'Telefoane Resigilate', 'Smartwatch-uri Resigilate', 'Resigilate Gaming']
XSUBCATS = ['resigilate', 'brand shop', 'brandshop', 'brand page', 'branduri', 'product finder']


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


def Request(url):
    r = agent.Request(url, proxies=['rotating-eu', 'rotating-us', 'eu', 'us'], force_charset='utf-8', use='curl')
    return r


def RequestProds(url, offset):
    options = """--globoff --compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101 Firefox/160.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: EMAGVISITOR=a%3A1%3A%7Bs%3A7%3A%22user_id%22%3Bi%3A2632759590977357610%3B%7D; ltuid=2632759590683255090; EMAGUUID=1795530791-2942520982-71370.695; site_version_11=not_mobile; eab1807=a; eab1813=b; eab1814=b; eab1815=a; eab1817=a; sr=1920x1032; vp=1920x902; loginTooltipShown=1; gdpr_consent_version=6; _pdr_internal=GA1.2.3108506052.1795530796; gdpr_consent_type=1; EMAGROSESSID=e9b618c27bfcab128b74db560bfdd054; _pdr_view_id=1795608109-14921.684-3334279967; AID=499b6be783beb9c73390d635b6720c84f8184d7f2109904d7c862b72c16c783f; token1=%222632759590977357610-80b361a6-9928-4882-9d41-8aa7071127e7-6b0691b3197524.87853861%22; cart_summary=%7B%22t%22%3A1%2C%22b%22%3A0%2C%22p%22%3A0%2C%22bfc%22%3A0%2C%22line%22%3A%5B%5D%7D; sr=1920x1032; vp=1920x664; _rsv=14; _rsdc=2; _rscd=1; customer_delivery_info={"g":0}; listingResetView=1; listingDisplayId=2; listingPerPage=100; eab1820=a; eab1821=a; aws-waf-token=16d45150-f023-44b9-a70e-f44e7dcc3614:CQoAa484vNP9JAAA:oW+n324w19VMOiUpGszIFRdFvubWg5C3LhWoZClK+UvT1xwoGWBDaHEsTxhCXnjgD1O1sq6JOkYO5Ji1cD3MIV48zXvqzlzQf05qVaZY2fTDb7SiA81IQ2q2nxqt8GuhTmPKYb++XTAW6UCkhYXG7h49DjR8tT9vDJ8WqN7MAXCkHiJ6GXsWi8vK9jS2HKqm+yLRCRi+IIScEf64LHx86Szj8FeEzDIpUSijVK/iN1/rhOAORWL4qQIJxMuE/LJjj/+e99C600xiUG3XDMLCckkJ7uPMgGFRyoDkQxHSYymTrjdG0J3Zfk/e+dKtXuOflPCiPZBAAx7ZJNoBR6LiTg8nQ2hveg==; postlogin=2xFixWR5ubqTOJVjm13%2BzuGCYW8v3YfUr8ozy8w37laog1zQMkvugZYJJjnqXmNH9RCEJOUnqEjdtn8YwZIHYMONrgCvwl%2F0f7lq8n5t77dTv7HQCMS5EZRAKA3NtNiMPmoT4JjNnDmR6k%2B00fX7gZRdbnyZYJXWqYpxDS3u5GA%3D; eab_allocation=' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""
    url = url.replace('https://www.emag.ro', '').split('?')[0].replace('/c', '/sort-reviewsdesc/c')
    url = 'https://www.emag.ro/search-by-url?source_id=7&templates[]=full&sort[reviews]=desc&listing_display_id=2&page[limit]=100&page[offset]={offset}&fields[items][image_gallery][fashion][limit]=2&fields[items][image][resized_images]=1&fields[items][resized_images]=200x200,350x350,720x720&fields[items][flags]=1&fields[items][offer][buying_options]=1&fields[items][offer][flags]=1&fields[items][offer][bundles]=1&fields[items][offer][gifts]=1&fields[items][characteristics]=listing&fields[quick_filters]=1&search_id=efad89ea1ec08151a20a&search_fraze=&search_key=&url={url}'.format(offset=offset, url=url)
    r = agent.Request(url, proxies=['rotating-eu', 'rotating-us', 'eu', 'us'], force_charset='utf-8', use='curl', options='-s -L --insecure '+options)
    return r


def RequestRevs(prod_path, offset):
    options = """--globoff --compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:160.0) Gecko/20100101 Firefox/160.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: EMAGVISITOR=a%3A1%3A%7Bs%3A7%3A%22user_id%22%3Bi%3A2632759590977357610%3B%7D; ltuid=2632759590683255090; EMAGUUID=1795530791-2942520982-71370.695; site_version_11=not_mobile; eab1807=a; eab1813=b; eab1814=b; eab1815=a; eab1817=a; sr=1920x1032; vp=1920x902; loginTooltipShown=1; gdpr_consent_version=6; _pdr_internal=GA1.2.3108506052.1795530796; gdpr_consent_type=1; EMAGROSESSID=e9b618c27bfcab128b74db560bfdd054; _pdr_view_id=1795608686-54181.403-3073806738; AID=499b6be783beb9c73390d635b6720c84f8184d7f2109904d7c862b72c16c783f; token1=%222632759590977357610-80b361a6-9928-4882-9d41-8aa7071127e7-6b0691b3197524.87853861%22; cart_summary=%7B%22t%22%3A1%2C%22b%22%3A0%2C%22p%22%3A0%2C%22bfc%22%3A0%2C%22line%22%3A%5B%5D%7D; sr=1920x1032; vp=1920x664; _rsv=14; _rsdc=2; _rscd=1; customer_delivery_info={"g":0}; listingResetView=1; listingDisplayId=2; listingPerPage=100; eab1820=a; eab1821=a; postlogin=2xFixWR5ubqTOJVjm13%2BzuGCYW8v3YfUr8ozy8w37laog1zQMkvugZYJJjnqXmNH9RCEJOUnqEjdtn8YwZIHYMONrgCvwl%2F0f7lq8n5t77dTv7HQCMS5EZRAKA3NtNiMPmoT4JjNnDmR6k%2B00fX7gZRdbnyZYJXWqYpxDS3u5GA%3D; eab_allocation=; aws-waf-token=16d45150-f023-44b9-a70e-f44e7dcc3614:CQoAigZpqb0qYAAA:HKxtC2p05LSMUWl4xwtHA8akkQ0PGAdv46l8Tuyun2RvzJDprdBriXr3DZXF2yV4YscXFN3CjNrEKTYSe/bifDOC9v7b8RkNfGn1iPXkglGRK4A+BkDGMvENtMnmntcDTY82RrKxBH9g93PFWb6jWVIW8FN6nKJQQ6QB4v0eBWGEpJ+G2gZOLvMJVtHQIqSSqLkvTofpOkcf+CmxzBfygk/dHCgsJCxe3vWtwFkEQHINopu32uAkxFBRaK963kCnlR5QzhtMLQe36TTDih2O/wCuVCdJEOmn3O2AY69F5ysbP+qJcQhp5rEU1S5cPtsRBiH5uA6T7poBLD8L7znKwwWCt/Xd/A==' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""
    url = 'https://www.emag.ro/product-feedback{prod_path}reviews/list?token=&page[offset]={offset}&page[limit]=20&sort[votes]=desc'.format(prod_path=prod_path, offset=offset)
    r = agent.Request(url, proxies=['rotating-eu', 'rotating-us', 'eu', 'us'], force_charset='utf-8', use='curl', options='-s -L --insecure '+options)
    return r


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.emag.ro'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "megamenu")]/a')
    for cat in cats:
        name = cat.xpath('.//span[contains(@class, "department-name")]//text() | .//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name and name not in XCAT and not any(xcat in name.lower() for xcat in XSUBCATS):
            if not url or 'javascript' in url:
                slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
                if slug:
                    url = 'https://www.emag.ro/' + slug.strip('-') + '/d'

            if url and not session.seen(url):
                session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//ul[contains(@class, "aside-links")]/li/a')
    for subcat in subcats:
        subcat_name = subcat.xpath('text()').string()
        url = subcat.xpath('@href').string()

        if url and subcat_name and subcat_name not in XCAT and not any(xcat in subcat_name.lower() for xcat in XSUBCATS) and not session.seen(url):
            if subcat_name not in context['cat']:
                cat_name = context['cat'] + '|' + subcat_name
            else:
                cat_name = context['cat']

            session.queue(Request(url), process_catlist, dict(cat=cat_name))

    if data.xpath('//h2[contains(@class, "card-v2-title")]'):
        cat_url = data.response_url
        session.queue(RequestProds(cat_url, 0), process_prodlist, dict(context, cat_url=cat_url))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    try:
        prods_json = simplejson.loads(data.content).get('data')
    except:
        prods_json = {}

    prods = prods_json.get('items', [])
    for prod in prods:
        product = dict()
        product['name'] = prod.get('name')
        product['ssid'] = str(prod.get('id'))
        product['mpn'] = prod.get('part_number_key')
        product['category'] = context['cat']

        prod_path = prod.get('url', {}).get('path')
        product['url'] = 'https://www.emag.ro' + prod_path

        revs_cnt = prod.get('feedback', {}).get('reviews', {}).get('count', 0)
        if revs_cnt and int(revs_cnt) > 0:
            if not session.seen(product['ssid']):
                session.queue(Request(product['url']), process_product, dict(product=product, revs_cnt=int(revs_cnt), prod_path=prod_path))
        else:
            return

    prods_cnt = context.get('prods_cnt', prods_json.get('pagination', {}).get('items_count', 0))
    offset = context.get('offset', 0) + 100
    if offset < prods_cnt:
        session.queue(RequestProds(context['cat_url'], offset), process_prodlist, dict(context, offset=offset, prods_cnt=prods_cnt))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    try:
        prod_json = data.xpath("""//script[contains(.,'"@type": "Product"')]//text()""").string()
        prod_json = simplejson.loads(prod_json)

        context['product']['manufacturer'] = prod_json.get('manufacturer', {}).get('name') or prod_json.get('brand', {}).get('name')
    except:
        pass

    session.queue(RequestRevs(context['prod_path'], 0), process_reviews, dict(context))


def process_reviews(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['product']['name']
    product.url = context['product']['url']
    product.ssid = context['product']['ssid']
    product.sku = product.ssid
    product.category = context['product']['category'].replace('||', '|').replace(' / ', '/').replace('Brand Shop', '').strip(' |')
    product.manufacturer = context['product'].get('manufacturer')

    mpn = context['product'].get('mpn')
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    try:
        revs = simplejson.loads(data.content).get('reviews', {}).get('items', [])
    except:
        revs = []

    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))

        date = rev.get('published')
        if date:
            review.date = date.split('T')[0]

        author = rev.get('user', {}).get('name')
        author_ssid = rev.get('user', {}).get('id')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rating')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.get('title')
        excerpt = rev.get('content_no_tags') or rev.get('content')
        if excerpt and len(remove_emoji(excerpt).strip()) > 2:
            if title:
                review.title = remove_emoji(title).strip()
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip()
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    offset = context.get('offset', 0) + 20
    if offset < context['revs_cnt']:
        session.queue(RequestRevs(context['prod_path'], offset), process_reviews, dict(context, offset=offset))
