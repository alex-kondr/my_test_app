from agent import *
from models.products import *


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
    session.queue(Request("https://www.clearchemist.co.uk/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "level0")]')
    for cat in cats:
        name = cat.xpath('a/span/text()').string()

        cats1 = cat.xpath('div[contains(@class, "element-inner")]/div')
        for cat1 in cats1:
            cat1_name = cat1.xpath('a/span/text()').string()

            cats2 = cat1.xpath('div[contains(@class, "element-inner")]/div')
            if cats2:
                for cat2 in cats2:
                    cat2_name = cat2.xpath('a/span/text()').string()

                    subcats = cat2.xpath('div[contains(@class, "element-inner")]/div/a')
                    if subcats:
                        for subcat in subcats:
                            subcat_name = subcat.xpath('span/text()').string()
                            url = subcat.xpath('@href').string()
                            
                            print name+'|'+cat1_name+'|'+cat2_name+'|'+subcat_name, url
                    else:
                        url = cat2.xpath('a/@href').string()
                        
                        print name+'|'+cat1_name+'|'+cat2_name, url
            else:
                url = cat1.xpath('a/@href').string()
                
                print name+'|'+cat1_name, url


def process_prodlist(data, context, session):
    prods = data.xpath('//li[contains(@class, "item product")]')
    for prod in prods:
        name = prod.xpath('.//a[@class="product-item-link"]/text()').string()
        url = prod.xpath('.//a[@class="product-item-link"]/@href').string()
        ssid = prod.xpath('.//div/@data-product-id').string()
        sku = prod.xpath('.//form/@data-product-sku').string()

        revs_cnt = prod.xpath('.//a[@class="action view"]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            revs_url = "https://www.clearchemist.co.uk/review/product/listAjax/id/{}/".format(ssid)
            session.queue(Request(revs_url), process_reviews, dict(context, name=name, url=url, ssid=ssid, sku=sku))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_reviews(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['cat'].replace('Shop|', '').strip(' |')
    product.ssid = context['ssid']

    sku = context.get('sku')
    if sku and sku.isdigit() == True and 11 < len(sku) < 15:
        product.properties.append(ProductProperty(type='id.ean', value=sku))
    elif sku:
        product.sku = sku

    revs = data.xpath("//li[@class='item review-item']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath('div[@class="review-title"]/text()').string()
        review.url = product.url
        review.type = 'user'
        review.date = rev.xpath('.//time/@datetime').string()

        author = rev.xpath('.//strong[@itemprop="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]/text()').string()
        if grade_overall:
            value = float(grade_overall.strip("%")) / 20
            review.grades.append(Grade(type='overall', value=float(value), best=5.0))

        excerpt = rev.xpath(".//div[@class='review-content']//text()").string(multiple=True)
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

            review.ssid = review.digest() if author else review.digest(excerpt)
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # No next_url
