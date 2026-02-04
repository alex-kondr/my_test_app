from agent import *
from models.products import *


XCAT = ["Home", "Blog", "About", "Contact", "Shop", "SALE !!!"]


def run(context, session):
    session.queue(Request("https://i4studio.nl/", use='curl'), process_catlist, dict())


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
                        session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name+'|'+subcat_name))
            else:
                url = cat.xpath("a/@href").string()
                session.queue(Request(url, use='curl'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath("//li[contains(@class, 'product type-product')]")
    for prod in prods:
        name = prod.xpath('.//a[contains(@class, "product__link")]/text()').string(multiple=True)
        url = prod.xpath('.//a[contains(@class, "product__link")]/@href').string()
        session.queue(Request(url, use='curl'), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page, use='curl'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = data.xpath('//div/@data-container_id').string()
    product.sku = product.ssid
    product.category = context["cat"]

    mpn = data.xpath('//span[@class="sku"]/text()').string()
    if mpn and ' ' not in mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath("//tr[contains(@class, '--attribute_ean')]/td//text()").string(multiple=True)
    if ean:
        product.add_property(type="id.ean", value=ean)

    context['product'] = product
    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//ol[@class="commentlist"]/li/div')
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

# """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: application/json, text/javascript, */*; q=0.01' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: https://i4studio.nl' -H 'Connection: keep-alive' -H 'Referer: https://i4studio.nl/studio-computers/daw-computer-audio-pc-digital-audio-workstation/diamond-audio-pc-aanbieding-14th-gen/' -H 'Cookie: cmplz_banner-status=dismissed; sbjs_migrations=1418474375998%3D1; sbjs_current_add=fd%3D2025-10-09%2010%3A13%3A18%7C%7C%7Cep%3Dhttps%3A%2F%2Fi4studio.nl%2F%7C%7C%7Crf%3D%28none%29; sbjs_first_add=fd%3D2025-10-09%2010%3A13%3A18%7C%7C%7Cep%3Dhttps%3A%2F%2Fi4studio.nl%2F%7C%7C%7Crf%3D%28none%29; sbjs_current=typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_first=typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_udata=vst%3D3%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%3B%20rv%3A147.0%29%20Gecko%2F20100101%20Firefox%2F147.0; wp-wpml_current_language=nl; cr_wpml_is_filtered=no' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Priority: u=0' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' --data-raw 'action=cr_show_more_all_reviews&attributes%5Bsort%5D=desc&attributes%5Bsort_by%5D=date&attributes%5Bper_page%5D=5&attributes%5Bshow_summary_bar%5D=true&attributes%5Bshow_media%5D=true&attributes%5Bshow_pictures%5D=false&attributes%5Bshow_products%5D=true&attributes%5Bproducts%5D%5B%5D=36417&attributes%5Bproduct_reviews%5D=true&attributes%5Bshop_reviews%5D=false&attributes%5Binactive_products%5D=false&attributes%5Bshow_replies%5D=false&attributes%5Bshow_more%5D=5&attributes%5Bmin_chars%5D=0&attributes%5Bavatars%5D=initials&attributes%5Busers%5D=all&attributes%5Badd_review%5D=false&attributes%5Bschema_markup%5D=false&page=1&search=&sort=recent'"""

    next_page = data.xpath('//a[@rel="next"]/@data-page').string()
    if next_page:
        next_url = 'https://judge.me/reviews/reviews_for_widget?url=i4studio.nl&shop_domain=i4studio.nl&platform=woocommerce&page={page}&per_page=5&product_id={ssid}'.format(page=next_page, ssid=product.ssid)
        session.do(Request(next_url, use='curl'), process_reviews, dict(product=product))

    elif product.reviews:
        session.emit(product)
