from agent import *
from models.products import *
import simplejson


XCAT = ['COLLECTIONS', 'ONLINE SPECIALS', 'SHOWROOM', 'Gift Vouchers', 'Gift Card', 'BESTSELLERS',]
XCAT2 = ["All ",' All']

DUPE_PRODS = []

def run(context: dict[str, str], session: Session):
    session.queue(Request("https://www.jekyllandhide.co.za/"), process_frontpage, dict())

def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[@class="header__primary-nav-item"]')
    for cat in cats:
        name = cat.xpath('@data-title').string()
        if name not in XCAT:

            cats1 = cat.xpath('.//ul[contains(@class, "mega-menu__linklist")]/li')
            for cat1 in cats1:
                cat1_name = cat1.xpath('a/text()').string()
                url = cat1.xpath('a/@href').string()
                if cat1_name not in XCAT:
                    subcats = cat1.xpath('ul/li/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('text()').string()
                            url = subcat.xpath('@href').string()
                            if not any(word in subcat_name for word in XCAT2):
                                # print(cat=name + '|' + cat1_name + '|' + subcat_name)
                                session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + cat1_name + '|' + subcat_name))
                    else:
                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + cat1_name))

def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//div[contains(@class, "product-card__info")]')
    for prod in prods:
        url = prod.xpath('.//a/@href').string()
        name = prod.xpath('.//a/text()').string()
        revs_count = prod.xpath('.//span[@class="rating-badge"]/@title').string()
        if revs_count:
            revs_count1 = int(revs_count.split()[0])
            if revs_count1 > 0:
                # print(name + '|' + url + '|' + revs_count)
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url, revs_count=revs_count))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))

def process_product(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.mpn = data.xpath('//div[@data-block-type="sku"]/text()[2]').string().split(':')[1]
    product.category = context['cat']

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type":"ProductGroup"')]//text()''').string())
        product.manufacturer = prod_json.get('brand', {}).get('name')

        json_text = simplejson.loads(data.xpath('''//script[contains(text(), '"@type":"Product"')]//text()''').string())
        prod_json = simplejson.loads(json_text)
        product.ssid1 = prod_json.get('hasVariant', [{}])[0].get('id')
        if product.ssid1:
            product.ssid1 = product.ssid1.replace("\\/", "/")
            if "=" in product.ssid1:
                product.ssid = product.ssid1.split("=")[1].split("#")[0]
        # else product.ssid1 = none

    except:
        print("----")
        print("name:", product.name)
        print("MPN", product.mpn)
        print("Category", product.category)
        print("Brand:",product.manufacturer)
        print("SSID:", product.ssid)
        print("----")

    # # revs_url = "https://www.kaiserkraft.de/api/shops/www.kaiserkraft.de/products/" + product.ssid + "/reviews?lang=de&page=1&reviewsPerPage=10"
    # # session.do(Request(revs_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_reviews, dict(product=product, revs_count=context['revs_count']))