from agent import *
from models.products import *
import simplejson
from datetime import datetime
import re


# XCAT = ['Senast inkommet', 'Adventskalendrar ', 'Julkit ']
# NO_SUBCATS = ['Brun utan sol']


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.hudoteket.se/", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="produkt"]/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        
        print name, url
        # if name and name not in XCAT:
        #     XCAT.append(name)
        # cats1 = cat.xpath('ul/li')
        # for cat1 in cats1:
        #     cat1_name = cat1.xpath('a/text()').string()

            # if cat1_name and cat1_name not in XCAT:
            #     XCAT.append(cat1_name)
            #     if cat1_name in NO_SUBCATS:
            #         # This category is somehow in "Man"
            #         url = cat1.xpath('a/@href').string()
                    
            #         print cat1_name, url
            #         # session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=cat1_name))
            #         continue

            # subcats = cat1.xpath('ul/li/a')
            # if subcats:
            #     for subcat in subcats:
            #         subcat_name = subcat.xpath('text()').string()
            #         url = subcat.xpath('@href').string()
                    
            #         print name+'|'+cat1_name+'|'+subcat_name, url
            #         # session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
            # else:
            #     url = cat1.xpath('a/@href').string()
                
            #     print name+'|'+cat1_name
            #     # session.queue(Request(url, force_charset='utf-8'), process_category, dict(cat=name+'|'+cat1_name))

def process_category(data, context, session):
    strip_namespace(data)

    cat_id = data.xpath("(//input[@name='artgrp'][@value!=''])[1]/@value").string()
    prods_cnt = data.xpath('//div[contains(., " artiklar")]/text()').string()
    if cat_id and prods_cnt:
        prods_cnt = prods_cnt.strip().split()[0]
        options = "-X POST -d 'funk=get_filter;limits=32;category_id={};offset=0;is_start=1;Visn=Std;Sort=Populara'".format(cat_id)
        session.do(Request("https://www.hudoteket.se/shop", force_charset='utf-8', options=options, max_age=0), process_prodlist, dict(context, cat_id=cat_id, prods_cnt=prods_cnt))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath("//div[@class='PT_Faktaruta']")
    for prod in prods:
        name = prod.xpath(".//a[@title]/text()").string()
        url = prod.xpath(".//a[@title]/@href").string()
        ssid = prod.xpath('.//input[@name="altnr"]/@value').string()
        if not ssid:
            ssid = prod.xpath('.//div[@class="QuickView-artnr"]/text()').string()

        session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url, ssid=ssid))

    offset = context.get("offset", 0) + 32
    if offset < int(context['prods_cnt']):
        options = "-X POST -d 'funk=get_filter;limits=32;category_id=" + context["cat_id"] + ";offset={};is_start=1;Visn=Std;Sort=Populara'".format(str(offset))
        session.do(Request("https://www.hudoteket.se/shop", use="curl", force_charset='utf-8', options=options, max_age=0), process_prodlist, dict(context, offset=offset))


def process_product(data, context, session):
    strip_namespace(data)

    prod_json = data.xpath('''//script[contains(., '"review":')]/text()''').string()
    if not prod_json:
        return

    prod_json = simplejson.loads(prod_json)

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.category = context["cat"]
    product.manufacturer = prod_json.get('brand', {}).get('name')
    product.ssid = context["ssid"]
    product.sku = product.ssid

    ean = prod_json.get('gtin8')
    if ean:
        product.properties.append(ProductProperty(type='id.ean', value=str(ean)))

    revs = prod_json.get('review')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url

        date = rev.get("datePublished")
        if date:
            review.date = datetime.strptime(date, "%Y%m%d").strftime("%Y-%m-%d")

        author = rev.get("author", {}).get("name")
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('reviewRating', {}).get('ratingValue')
        if grade_overall or grade_overall == 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        excerpt = rev.get("description")
        if excerpt and excerpt.strip():
            excerpt = re.sub(r'&#\d+;?', '', excerpt).replace('<br>', '')

            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next page
