from agent import *
from models.products import *
import simplejson


XCAT = ["Magazijn", "Kantoorartikelen", "Bekabeling", "Drinken", "Eten", "Schrijfgerei", "Notebooks", "Schrijfmap", "Sleutelhanger"]
X_CONS = ['nvt', 'Geen', 'geen', 'niets', 'nothing', 'Nothing', 'niet', 'n.v.t', 'N.v.t', 'Niets', 'GEEN', '0']
X_PROS = ['nvt', 'n.v.t', 'geen', 'GEEN', 'Geen', 'N.v.t']


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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.office-deals.nl/"), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//li[@class="main-category"]/a')
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    subcats = data.xpath('//div[@class="manufacturerlist"]/a')
    for subcat in subcats:
        name = subcat.xpath('.//h2/text()').string()
        url = subcat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_catlist, dict(cat=context['cat']+'|'+name))

    if not subcats:
        process_prodlist(data: Response, context: dict[str, str], session: Session)


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    prods = data.xpath('//p[@itemprop="name"]/a')
    for prod in prods:
        name = prod.xpath('@title').string()
        url = prod.xpath("@href").string()

        if name and url:
            url = url.split('?')[0]
            session.queue(Request(url, use="curl"), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@title, "Volgende pagina")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath("//p[contains(text(), 'Artikelnummer:')]/span/text()").string()
    product.sku = product.ssid
    product.category = context["cat"]
    product.manufacturer = data.xpath('//div[@id="single-product"]//p[contains(., "Merk:")]/a/text()').string(multiple=True)

    prod_json = data.xpath("""//script[@type="application/ld+json"][contains(., '"@type" : "Product"')]/text()""").string()
    try:
        resp = simplejson.loads(prod_json)

        if not product.manufacturer:
            product.manufacturer = resp.get('brand', {}).get('name')

        product.sku = resp.get('sku')

        ean = resp.get('gtin')
        if ean and str(ean).isdigit() and len(str(ean)) > 10:
            product.add_property(type="id.ean", value=str(ean))
    except:
        pass

    revs = data.xpath("//div[@class='product-review']")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('.//p[contains(strong, "Datum")]/span/text()').string()

        author_name = rev.xpath('.//p[contains(strong, "Naam")]/span/text()').string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        grade_overall = rev.xpath(".//div[@class='rating']/@style").string()
        if grade_overall:
            grade_overall = float(grade_overall.split(':')[-1].split('%')[0]) / 20
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

        grades = rev.xpath(".//div[@class='row review-row'][.//div[@class='rating_bar']]/div")
        for grade in grades:
            name = grade.xpath(".//strong/text()").string()
            grade_val = grade.xpath(".//div[@class='rating']/@style").string()
            if name and grade_val:
                grade_val = float(grade_val.split(':')[-1].split('%')[0]) / 20
            review.grades.append(Grade(name=name, value=float(grade_val), best=5.0))

        is_recommended = rev.xpath(".//p[@class='recommend']//span[@class='thumbup']")
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.xpath('.//li[@class="do-like"]/text()').string(multiple=True)
        if hlp_yes and int(hlp_yes) > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//li[@class="do-not-like"]/text()').string()
        if hlp_no and int(hlp_no) > 0:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        EXISTED_PROS = []
        pros = rev.xpath('.//ul[@class="plus-minus-listing plus-listing"]/li')
        for pro in pros:
            pro = pro.xpath("text()").string().strip('+. ')
            if pro and pro not in X_PROS and pro not in EXISTED_PROS:
                EXISTED_PROS.append(pro)
                review.add_property(type="pros", value=pro)

        EXISTED_CONS = []
        cons = rev.xpath('.//ul[@class="plus-minus-listing minus-listing"]/li')
        for con in cons:
            con = con.xpath("text()").string().strip('-. ')
            if con and con not in X_CONS and con not in EXISTED_CONS:
                EXISTED_CONS.append(con)
                review.add_property(type="cons", value=con)

        title = rev.xpath(".//h2//text()").string(multiple=True)
        excerpt = rev.xpath(".//div[contains(h3, 'Beschrijving')]/p//text()").string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author_name else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# loaded all revs
