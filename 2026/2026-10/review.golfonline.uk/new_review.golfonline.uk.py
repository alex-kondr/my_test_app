from agent import *
from models.products import *


XCAT = ['Gifts', 'Brands', 'Sale', 'Help']


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
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.golfonline.co.uk/', use='curl', force_charset='utf-8'), process_frontpage, {})


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="bC_Menu"]/li[@data-catid]/a')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url+'?sortColumn=3&sortDirection=2', use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//nav[contains(@class, "subcategories")]/a')
    if not cats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)
        return

    for cat in cats:
        name = cat.xpath('span[contains(@class, "title")]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url+'?sortColumn=3&sortDirection=2', use='curl', force_charset='utf-8'), process_catlist, dict(cat=context['cat']+'|'+name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//article[@data-productid]')
    for prod in prods:
        name = prod.xpath('.//h3[contains(@class, "title")]//text()').string(multiple=True)
        ssid = prod.xpath('@data-productid').string()
        url = prod.xpath('.//h3[contains(@class, "title")]/a/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "card__rev")]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.split()[-1].strip('( )'))
            if revs_cnt > 0:
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, url=url, name=name, ssid=ssid, revs_cnt=revs_cnt))
        else:
            return

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['ssid']
    product.sku = data.xpath('//span[@id="productCodes"]/span/text()').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()

    prod_info = data.xpath('//script[contains(., "ManufacturerCode")]/text()').string()
    if prod_info:
        mpn = prod_info.split('"ManufacturerCode":"', 1)[-1].split('","', 1)[0]
        if mpn and len(mpn) > 5:
            product.add_property(type='id.manufacturer', value=mpn)

    revs = data.xpath('//div[@class="reviewSection"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']

        date = rev.xpath('.//time/@datetime').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//a[@class="reviewSection_Username"]/@data-name').string()
        author_ssid = rev.xpath('.//a[@class="reviewSection_Username"]/@data-customerid').string()
        if author and author_ssid and 'anonymous' not in author.lower():
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author and 'anonymous' not in author.lower():
            review.authors.append(Person(name=author, ssid=author))
        else:
            author = None

        grade_overall = rev.xpath('.//div[@class="reviewSectionOverallRating"]/b/@class').string()
        if grade_overall:
            grade_overall = float(grade_overall.split('Star')[-1]) / 10.
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = rev.xpath('.//div[@class="reviewSectionRatings"]/div')
        for grade in grades:
            grade_name = grade.xpath('i/text()').string().strip(' :')
            grade_value = grade.xpath('span/@class').string().split('block')[-1]
            if grade_name and grade_value:
                review.grades.append(Grade(name=grade_name, value=float(grade_value), best=5.0))

        is_verified = rev.xpath('.//b[@data-title="Confirmed Buyer"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev.xpath('.//dl//dd[contains(., "Yes")]')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        title = rev.xpath('.//h4[@class="reviewSectionH4"]/text()').string()
        excerpt = rev.xpath('.//p[@class="reviewSection_ReviewText"]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# loaded all reviews
