from agent import *
from models.products import *
import simplejson

XCAT = ['Accessories and options', 'Quality refurbished', 'Carton damaged', 'Ink and paper clearance', 'Epson CoverPlus', 'Inks and papers']


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.epson.com.au/shoponline/'), process_catlist, dict())
    # session.queue(Request('https://www.epson.com.au/products/multifunctional/ExpressionHomeXP-3105_userreviews.asp'), process_product, {'product_url': '1', 'category_name': '2'}) 


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[@class="card-block"]')
    for cat in cats:
        url = cat.xpath('.//a[@class="btn btn-primary"]/@href').string()
        name = cat.xpath('.//h3/text()').string()
        if name and name not in XCAT:
           session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods_json = data.xpath('//div[@class="product-results"]/script//text()').string()
    if not prods_json:
        return

    prods = simplejson.loads(prods_json.split("const products = ")[-1].rstrip(";"))
    for prod in prods:
        product = Product()
        product.name = prod['Name']
        product.category = context['cat']
        product.ssid = prod['ProductID']
        product.manufacturer = 'Epson'
        product.url = 'https://www.epson.com.au/products/{}/{}/{}'.format(prod['MainCategory'], prod['SubCategory'], product.ssid)
        mpn = prod.get('Globalcode')

        revs_count = prod.get('TotalReviews')
        if revs_count and int(revs_count) > 0 and mpn:
            product.add_property(type='id.manufacturer', value=mpn)

            revs_url = 'https://epsonenau.ugc.bazaarvoice.com/5625-en_au/{}/reviews.djs?format=embeddedhtml&scrollToTop=true&page=1'.format(mpn)
            session.do(Request(revs_url), process_reviews, dict(context, product=product))


def process_reviews(data: Response, context: dict[str, str], session: Session):

    product = context['product']

    revs_html = data.content.split('{"BVRRRatingSummarySourceID":" ')[-1].split('initializers')[0].strip().rstrip('"},')
    revs_html = data.parse_fragment(revs_html)
    # revs_html.pretty()
    # exit()

    revs = revs_html.xpath('''//div[@class='\\"BVRRReviewTextContainer\\"']''')
    for rev in revs:
        rev.pretty()
        exit()
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string()

        




#  session.queue(Request(url), process_product, dict(context, url=url, name=name, ssid=ssid, mpn=mpn, revs_count=revs_count))

    # revs_url = 
        # session.queue(Request(revs_url, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_reviews, dict(context, name=name, url=url, ssid=ssid, mpn=mpn, revs_count=context['revs_count']))