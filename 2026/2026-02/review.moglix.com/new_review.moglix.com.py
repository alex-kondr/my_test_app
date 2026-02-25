from agent import *
from models.products import *
import simplejson


XCAT = ['Ink Cartridges', 'Paper & Notebooks', 'Softwares', 'Gifts & Combos', 'Wires & Cables', 'Wire & Cable Accessories', 'Paints & Coatings', 'USB Data Cables', 'Mobile Cases & Covers', 'Mobile Screen Guards', 'Aux Cables', 'Mobile Camera Protectors', 'Network Cables', 'Services']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    options = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: FastAB=f508f010-e3f2-4ac5-aaef-04b0cb05271e; PWA=true; AB_TESTING=false; BUILD_VERSION=DESKTOP-14.0.0; ph_phc_IQEVTwEvx55KZRh66MjBfecgDF9bmIVWd7w2QaYzylS_posthog=%7B%22%24device_id%22%3A%22019c89d1-12fc-72a1-96ed-cd4c7a97b834%22%2C%22distinct_id%22%3A%22019c89d1-12fc-72a1-96ed-cd4c7a97b834%22%2C%22%24sesid%22%3A%5B1771839132867%2C%22019c89d1-13f0-7727-b03b-c9632a453646%22%2C1771838706672%5D%2C%22%24initial_person_info%22%3A%7B%22r%22%3A%22%24direct%22%2C%22u%22%3A%22https%3A%2F%2Fwww.moglix.com%2Fall-categories%22%7D%7D' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""
    session.queue(Request('https://www.moglix.com/all-categories', use='curl', force_charset='utf-8', options=options), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="all-cate-section pad-15"]')
    for cat in cats:
        name = cat.xpath('h3[@class="red-txt"]/text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('.//div[@class="cate-type"]')
            if cats1:
                for cat1 in cats1:
                    cat1_name = cat1.xpath('.//strong[@*[contains(name(), "data-_ngcontent-sc")]]/text()').string()

                    if cat1_name not in XCAT:
                        subcats = cat1.xpath('a[not(strong)]')
                        if subcats:
                            for subcat in subcats:
                                subcat_name = subcat.xpath('text()').string()
                                url = subcat.xpath('@href').string()

                                if subcat_name not in XCAT:
                                    session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
                        else:
                            url = cat1.xpath('a[strong]/@href').string()
                            session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + cat1_name))
            else:
                url = cat.xpath('a/@href').string()
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[div[@class="brand"]]')
    for prod in prods:
        name = prod.xpath('div[@class="name"]//span/text()').string()
        manufacturer = prod.xpath('div[contains(@class, "brand")]/span/text()').string()
        url = prod.xpath('div[@class="name"]/a/@href').string()

        revs = prod.xpath('.//span[starts-with(@class, "count")]/text()')
        if revs:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].upper()
    product.sku = product.ssid
    product.category = context['cat'].replace('Other ', '').strip()

    manufacturer = context['manufacturer']
    if manufacturer:
        product.manufacturer = manufacturer.replace('By:', '').strip().title()

    mpn = data.xpath('//tr[td[contains(., "Item Code")]]/td[@class="right"]//text()').string(multiple=True)
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    revs_url = product.url.replace('https://www.moglix.com/', 'https://www.moglix.com/product-reviews/')
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="reviewRow"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.date = rev.xpath('.//p[contains(@class, "date")]/text()').string()

        author = rev.xpath('.//p[@class="customer-name"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('count(.//i[contains(@class, "green-txt")])')
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

        is_verified = rev.xpath('.//p[contains(., "Verified Purchase")]')
        if is_verified:
            review.add_property(type="is_verified_buyer", value=True)

        helpful = rev.xpath('.//button[i[contains(@class, "icon-like")]]/span/text()').string()
        if helpful and helpful.isdigit() and int(helpful) > 0:
            review.add_property(type='helpful_votes', value=int(helpful))

        not_helpful = rev.xpath('.//button[i[contains(@class, "icon-dislike ")]]/span/text()').string()
        if not_helpful and not_helpful.isdigit() and int(not_helpful) > 0:
            review.add_property(type='not_helpful_votes', value=int(not_helpful))

        title = rev.xpath('.//p[contains(@class, "heading")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@class="content"]//text()').string(multiple=True)
        if excerpt and len(excerpt) > 2:
            if title != excerpt:
                review.title = title.strip()
        else:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# not next page
