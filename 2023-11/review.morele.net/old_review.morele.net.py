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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.morele.net/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//a[@class="cn-departments-name cn-link cn-name"]')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//a[@class="col-xs-12 col-md-6 col-lg-4 col-xl-3"]')
    for cat in cats:
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_category, dict())


def process_category(data, context, session):
    subcats = data.xpath('//a[@class="col-xs-12 col-md-6 col-lg-4 col-xl-3"]')
    for subcat in subcats:
        url = subcat.xpath('@href').string() + ",,,,,,,rc,1,,,,/"
        name = data.xpath('//h1[@class="item-title "]//text()').string()
        session.queue(Request(url), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="cat-product card"]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('@data-product-name').string()
        product.category = context['cat'] + "|" + data.xpath('//span[@class="category-name"]//text()').string()
        product.ssid = prod.xpath('@data-product-id').string()
        product.manufacturer = prod.xpath('@data-product-brand').string()
        product.url = prod.xpath('.//a[@class="productLink"]/@href').string()

        if product.url == "https://www.morele.net/ubezpieczenie-3-lata-od-zakupu-dodatkowy-rok-gwarancji-602818/":
            return

        revs_count = prod.xpath('.//div[@class="stars-box  "]//span[@class="rating-count"]//text()').string()
        revs_url = product.url + "?sekcja=reviews-all"

        if revs_count:
            session.queue(Request(product.url), process_product, dict(product=product, revs_url=revs_url, page=1))
        else:
            return

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = context['product']
    product.sku = data.xpath('//span[@itemprop="sku"]//text()').string()

    ean = data.xpath('//span[@itemprop="gtin13"]//text()').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@itemprop="review"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.ssid = rev.xpath('@data-review-id').string()
        review.date = rev.xpath('.//div[@class="rev-date"]//text()').string()

        author = rev.xpath('.//div[@class="rev-author"]//text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@itemprop="ratingValue"]//text()').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.xpath('.//i[@class="icon-purchase-verified"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[@class="positive-rate-count"]//text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[@class="negative-rate-count"]//text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        pros = rev.xpath('.//ul[@class="rev-good"]/li[position() > 1]')
        if pros:
            for pro in pros:
                pro = pro.xpath('.//text()').string(multiple=True).replace('+', '').strip()
                if pro != '':
                    review.add_property(type="pros", value=pro)

        cons = rev.xpath('.//ul[@class="rev-bad"]/li[position() > 1]')
        if cons:
            for con in cons:
                con = con.xpath('.//text()').string(multiple=True).replace('-', '').strip()
                if con != '':
                    review.add_property(type="cons", value=con)

        excerpt = rev.xpath('.//div[@class="rev-desc"]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    revs_count = int(data.xpath('//span[@itemprop="reviewCount"]//text()').string())
    per_page = 20
    next_page = context['page'] + 1

    if revs_count > per_page:
        page_count = revs_count // per_page

        if revs_count % per_page > 0:
            page_count += 1

        url = context["revs_url"] + "&reviews_page={}".format(next_page)

        if next_page <= page_count:
            session.do(Request(url), process_product, dict(context, product=product, page=next_page))
            return

    if product.reviews:
        session.emit(product)
