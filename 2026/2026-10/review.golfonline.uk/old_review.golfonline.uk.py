import simplejson
from agent import *
from models.products import *
import re


def serialize_text(text):
    text = re.sub(r'&([a-zA-Z]+);', lambda match: '&' + match.group(1).lower() + ';', text).replace('<br />', ' ').replace('<br/>', ' ').replace('<br/', ' ').replace("\r", "").replace("\n", "").replace('\t', '').replace('&', '&').replace('°', '°').replace('œ', 'œ').replace('í', 'í').replace('ú', 'ú').replace('“', '"').replace('£', '£').replace('"', '"').replace('à', 'à').replace('é', 'é').replace('á', 'á').replace('´', '́').replace('ã', 'ã').replace('ç', 'ç').replace('ó', 'ó').replace('€', '€').replace('ê', 'ê').replace('è', 'è').replace('’', '’').replace('”', '”').replace(' ', ' ').replace('<', '<').replace('>', '>').replace('‘', '‘').replace('–', '–').replace('ä', 'ä').replace('ß', 'ß').replace('ö', 'ö').replace('ü', 'ü').replace('â', 'â').replace('õ', 'õ').replace('ø', 'ø').replace('…', '…').replace('„', '„').replace('—', '—')
    return text


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.golfonline.co.uk/'), process_frontpage, {})


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="bC_Menu"]/li[@data-catid]/a')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_category, dict(cat=name))


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//section[@id="categoryLHNav" or header[contains(., "Categories")]]/nav[preceding-sibling::*[1][self::header[contains(., "Categories")]]]/ul//a[not(@class="viewmoreclick" or contains(., "Show All"))]')
    if not cats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for cat in cats:
        name = cat.xpath('text()').string() or cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_category, dict(cat=context['cat']+'|'+name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//b[@data-productid][.//b[@class="rating"]/span[contains(@class, "FilledStar")]]')
    for prod in prods:
        name = prod.xpath('a[@class="pT"]/b/text()').string()
        url = prod.xpath('a[@class="pT"]/@href').string()
        ssid = prod.xpath('@data-productid').string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']

    prod_json = data.xpath('''//script[contains(., '"@type":"Product"')]/text()''').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        manufacturer = prod_json.get('brand', {})
        if manufacturer:
            product.manufacturer = serialize_text(manufacturer.get('name')).strip()

        product.sku = prod_json.get('productID')

        ean = prod_json.get('gtin13')
        if ean:
            product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

        mpn = prod_json.get('mpn')
        if mpn:
            product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs = data.xpath('//div[@class="reviewSection"]')
    for rev in revs:
        if rev.xpath('.//div[@class="reviewSection"]'):
            continue    # A page can be broken sometimes and has the same sub-element

        review = Review()
        review.type = 'user'
        review.url = context['url']

        review.title = rev.xpath('.//h4[@class="reviewSectionH4"]/text()').string()
        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//a[@class="reviewSection_Username"]').first()
        if author:
            author_name = author.xpath('@data-name').string()
            author_ssid = author.xpath('@data-customerid').string()
            url = author.xpath('@href').string()    # "This reviewer profile is not currently available"
            if author_name and author_ssid:
                review.authors.append(Person(name=author_name, ssid=author_ssid))

        is_verified = rev.xpath('.//b[@data-title="Confirmed Buyer"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.xpath('.//dl//dd[contains(., "Yes")]')
        if is_recommended:
            review.properties.append(ReviewProperty(value=True, type='is_recommended'))

        grades = rev.xpath('.//div[@class="reviewSectionRatings"]/div')
        for grade in grades:
            grade_name = grade.xpath('i/text()').string().strip(' :')
            grade_value = grade.xpath('span/@class').string().split('block')[-1]
            if grade_name and grade_value:
                review.grades.append(Grade(name=grade_name, value=float(grade_value), best=5.0))

        grade_overall = rev.xpath('.//div[@class="reviewSectionOverallRating"]/b/@class').string()
        if grade_overall:
            grade_overall = int(grade_overall.split('Star')[-1]) / 10.
            review.grades.append(Grade(name='Overall', type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//p[@class="reviewSection_ReviewText"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)