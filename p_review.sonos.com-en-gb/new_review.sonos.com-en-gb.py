from agent import *
from models.products import *
from datetime import datetime
import simplejson


def run(context, session):
    session.queue(Request('https://www.sonos.com/en/shop'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//a[@data-test-id="cart-link-container"]')
    for prod in prods:
        url = prod.xpath('@href').string()
        session.queue(Request(url), process_product, dict(url=url))

    # No next URL, all products are on a single page

def process_product(data, context, session):
    resp_html = data.xpath('//script[@data-test-id="jsonLd"]//text()').string()
    if resp_html:
        resp = simplejson.loads(resp_html)
        product_info = resp['offers']

        product = Product()
        product.url = context['url']
        product.category = data.xpath('(//a[@class="oe5jis2"])[position() = last()]//text()').string()
        product.name = resp['name']
        product.manufacturer = resp['brand']['name']

        if type(product_info) is list:
            mpn = resp['offers'][-1]['itemOffered']['sku']
            ean = resp['offers'][-1]['itemOffered'].get('gtin12')
        else:
            mpn = resp['sku']
            ean = resp.get('gtin12')
        
        product.ssid = mpn

        if ean:
            product.add_property(type='id.ean', value=ean)

        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ssid = product.url.split('/')[-1]
        revs_url = 'https://display.powerreviews.com/m/923023/l/en_US/product/{}/reviews?paging.from=0&paging.size=25&filters=&search=&sort=Newest&image_only=false&page_locale=en_US&_noconfig=true&apikey=cc48e875-2a83-4fb9-a513-164a041971fa'.format(ssid)
        session.do(Request(revs_url, force_charset="utf-8", use="curl"), process_reviews, dict(product=product))
        
        if product.reviews:
            session.emit(product)


def process_reviews(data, context, session):
    product = context['product']

    rev_content = data.xpath('//body//text()').string()
    if rev_content:
        resp = simplejson.loads(data.content.replace("{}\r\n", ''))
        revs = resp["results"][0]["reviews"]

        for rev in revs:
            review = Review()
            review.type = 'user'
            review.url = product.url
            review.title = rev["details"]["headline"]
            review.ssid = str(rev["review_id"])

            date = rev["details"]["created_date"]
            review.date = datetime.utcfromtimestamp(date / 1000).strftime('%d.%m.%Y')

            grade_overall = rev["metrics"]["rating"]
            if grade_overall:
                review.grades.append(Grade(type="overall", value=grade_overall, best=5.0))

            author_name = rev["details"]["nickname"]
            if author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

            review.add_property(type="is_verified_buyer", value=rev["badges"]["is_verified_buyer"])

            props = rev["details"]["properties"]
            for prop in props:
                if prop["key"] == "pros":
                    pros = prop["value"]
                    for pro in pros:
                        review.add_property(type="pros", value=pro)
                elif prop["key"] == "cons":
                    cons = prop["value"]
                    for con in cons:
                        review.add_property(type="cons", value=con)

            excerpt = rev["details"]["comments"]
            if excerpt:
                excerpt = excerpt.encode("ascii", errors="ignore").replace("\r\n", "").replace("\r", "").replace("\n", "")
                review.add_property(type="excerpt", value=excerpt)
                product.reviews.append(review)

        next_page = resp['paging'].get('next_page_url')
        if next_page:
            url = 'https://display.powerreviews.com' + next_page + '&_noconfig=true&apikey=cc48e875-2a83-4fb9-a513-164a041971fa'
            session.do(Request(url, force_charset="utf-8", use="curl"), process_reviews, dict(product=product))

