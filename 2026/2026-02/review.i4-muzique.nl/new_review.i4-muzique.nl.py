from agent import *
from models.products import *
import simplejson


XCAT = ["Home", "Blog", "About", "Contact", "Shop", "SALE !!!"]


def run(context, session):
    session.queue(Request("https://i4studio.nl/", use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath("//ul[@id='menu-nieuw']/li")
    for cat in cats:
        name = cat.xpath("a//text()").string(multiple=True)

        if name not in XCAT:
            subcats = cat.xpath("div/div/ul/li")
            if subcats:
                for subcat in subcats:
                    subcat_name = subcat.xpath("a//text()").string(multiple=True)
                    url = subcat.xpath("a/@href").string()

                    if subcat_name not in XCAT:
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+subcat_name))
            else:
                url = cat.xpath("a/@href").string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//li[contains(@class, 'product type-product')]")
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product__link")]/text()').string(multiple=True)
        url = prod.xpath('.//a[contains(@class, "product__link")]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.sku = product.ssid
    product.category = context["cat"]

    product.ssid = data.xpath('//div/@data-container_id').string()
    if not product.ssid:
        product.ssid = product.url.split('/')[-2]

    mpn = data.xpath('//span[@class="sku"]/text()').string()
    if mpn and ' ' not in mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath("//tr[contains(@class, '--attribute_ean')]/td//text()").string(multiple=True)
    if ean:
        product.add_property(type="id.ean", value=ean)

    revs_cnt = data.xpath('//div[contains(@class, "rating-count")]/text()').string()
    if revs_cnt:
        revs_cnt = int(revs_cnt.replace('Gebaseerd op ', '').split('beoordeli')[0])
        if revs_cnt > 0:
            context['product'] = product
            context['revs_cnt'] = revs_cnt
            process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    if context.get('offset'):
        revs_json = simplejson.loads(data.content)
        new_data = data.parse_fragment(revs_json.get('html'))
        revs = new_data.xpath('//div[contains(@class, "comment_container")]')
    else:
        revs = data.xpath('//div[contains(@class, "comment_container")]')

    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.xpath(".//time/@datetime").string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath(".//span[contains(@class, 'review__author')]/text()[not(contains(., 'Anoniem'))]").string(multiple=True)
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[contains(@class, "star-rating")]/@aria-label').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Gewaardeerd', '').split(' uit ')[0]
            if grade_overall and float(grade_overall):
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//div[contains(@class, "avatar-check")]').string()
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        excerpt = rev.xpath('.//div[@class="description"]//p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            ssid = rev.xpath('@id').string()
            if ssid:
                review.ssid = ssid.replace('comment-', '')
            else:
                review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)


    offset = context.get('offset', 0) + 5
    if offset < context['revs_cnt']:
        next_page = context.get('page', 0) + 1
        options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: https://i4studio.nl' -H 'Connection: keep-alive' -H 'Referer: https://i4studio.nl/studio-computers/daw-computer-audio-pc-digital-audio-workstation/diamond-audio-pc-aanbieding-14th-gen/' -H 'Cookie: cmplz_banner-status=dismissed; sbjs_migrations=1418474375998%3D1; sbjs_current_add=fd%3D2025-10-09%2010%3A13%3A18%7C%7C%7Cep%3Dhttps%3A%2F%2Fi4studio.nl%2F%7C%7C%7Crf%3D%28none%29; sbjs_first_add=fd%3D2025-10-09%2010%3A13%3A18%7C%7C%7Cep%3Dhttps%3A%2F%2Fi4studio.nl%2F%7C%7C%7Crf%3D%28none%29; sbjs_current=typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_first=typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_udata=vst%3D3%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%3B%20rv%3A147.0%29%20Gecko%2F20100101%20Firefox%2F147.0; wp-wpml_current_language=nl; cr_wpml_is_filtered=no' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw 'action=cr_show_more_all_reviews&attributes%5Bsort%5D=desc&attributes%5Bsort_by%5D=date&attributes%5Bper_page%5D=5&attributes%5Bshow_summary_bar%5D=true&attributes%5Bshow_media%5D=true&attributes%5Bshow_pictures%5D=false&attributes%5Bshow_products%5D=true&attributes%5Bproducts%5D%5B%5D={ssid}&attributes%5Bproduct_reviews%5D=true&attributes%5Bshop_reviews%5D=false&attributes%5Binactive_products%5D=false&attributes%5Bshow_replies%5D=false&attributes%5Bshow_more%5D=5&attributes%5Bmin_chars%5D=0&attributes%5Bavatars%5D=initials&attributes%5Busers%5D=all&attributes%5Badd_review%5D=false&attributes%5Bschema_markup%5D=false&page={page}&search=&sort=recent'""".format(ssid=product.ssid, page=next_page)
        url = 'https://i4studio.nl/wp-admin/admin-ajax.php'
        session.do(Request(url, use='curl', options=options, force_charset='utf-8', max_age=0), process_reviews, dict(context, product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
