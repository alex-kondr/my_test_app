from agent import *
from models.products import *
import simplejson


XCAT = ["Magazijn", "Kantoorartikelen", "Bekabeling", "Drinken", "Eten", "Schrijfgerei", "Notebooks", "Schrijfmap", "Sleutelhanger"]
X_CONS = ['nvt', 'Geen', 'geen', 'niets', 'nothing', 'Nothing', 'niet', 'n.v.t', 'N.v.t', 'Niets', 'GEEN', '0']
X_PROS = ['nvt', 'n.v.t', 'geen', 'GEEN', 'Geen', 'N.v.t']

def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.office-deals.nl/", use="curl", force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats1 = data.xpath('//li[@class="main-category"]')
    for cat1 in cats1:
        cat1_name = cat1.xpath("a/text()").string()

        if cat1_name not in XCAT:
            cats2 = cat1.xpath('.//li[@class="main-child"]')
            for cat2 in cats2:
                cat2_name = cat2.xpath("a/text()").string()

                if cat2_name not in XCAT:
                    url = cat2.xpath("a/@href").string()
                    cats3 = cat2.xpath('following-sibling::li[@class="sub-child"]/a')
                    if not cats3:
                        url = url.split('?')[0]
                        session.queue(Request(url, use="curl", force_charset='utf-8'), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))

                    for cat3 in cats3:
                        cat3_name = cat3.xpath("text()").string()
                        url = cat3.xpath("@href").string()
                        if cat3_name not in XCAT:
                            if cat3_name == cat2_name:
                                cat3_name = ''
                            url = url.split('?')[0]
                            session.queue(Request(url, use="curl", force_charset='utf-8'), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    prods = data.xpath('//p[@itemprop="name"]//a')
    for prod in prods:
        name = prod.xpath('@title').string()
        url = prod.xpath("@href").string()
        if name and url:
            url = url.split('?')[0]
            session.queue(Request(url, use="curl"), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(@title, "Volgende pagina")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    revs_cnt = data.xpath('//a[contains(@class, "review_link")]/text()').string()
    if not revs_cnt or revs_cnt and int(revs_cnt.split()[0]) < 1:
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context["cat"].strip(' |')
    product.manufacturer = data.xpath('//div[@id="single-product"]//span[contains(., "Merk:")]/a/text()').string()
    product.ssid = data.xpath("//span[contains(text(), 'Artikelnummer:')]/span/text()").string()
    product.sku = product.ssid

    prod_json = data.xpath("""//script[@type="application/ld+json"][contains(., '"@type" : "Product"')]/text()""").string()
    if prod_json:
        resp = simplejson.loads(prod_json)

        if not product.manufacturer:
            product.manufacturer = resp.get('brand', {}).get('name')

        mpn = resp.get('sku')
        if mpn:
            product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

        ean = resp.get('gtin')
        if ean:
            product.add_property(type="id.ean", value=str(ean))

    revs = data.xpath("//div[@class='product-review']")
    for rev in revs:
        review = Review()
        review.title = rev.xpath(".//h2//text()").string(multiple=True).strip()
        review.url = product.url
        review.type = "user"

        date = rev.xpath('.//strong[contains(., "Datum")]/following-sibling::span/text()').string()
        if date:
            review.date = '-'.join(date.split('/')[::-1])

        author_name = rev.xpath('.//strong[contains(., "Naam")]/following-sibling::span/text()').string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        is_recommended = rev.xpath(".//p[@class='recommend']//span[@class='thumbup']")
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.xpath('.//span[i[@class="icon-thumbs-up"]]/text()').string()
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        hlp_no = rev.xpath('.//span[i[@class="icon-thumbs-down"]]/text()').string()
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        grade_overall = rev.xpath(".//div[@class='rating']/@style").string()
        if grade_overall:
            grade_overall = float(grade_overall.split(':')[-1].split('%')[0]) / 20
            review.grades.append(Grade(type="overall", value=round(grade_overall, 2), best=5.0))

        grades = rev.xpath(".//div[@class='row review-row'][.//div[@class='rating_bar']]/div")
        for grade in grades:
            name = grade.xpath(".//strong/text()").string()
            value = float(grade.xpath(".//div[@class='rating']/@style").string().split(':')[-1].split('%')[0]) / 20
            review.grades.append(Grade(name=name, value=round(value, 2), best=5.0))

        EXISTED_PROS = []
        pros = rev.xpath('.//span[i[@class="icon-plus-circle"]]')
        for pro in pros:
            pro = pro.xpath("text()").string().strip('+. ')
            if pro and pro not in X_PROS and pro not in EXISTED_PROS:
                EXISTED_PROS.append(pro)
                review.add_property(type="pros", value=pro)

        EXISTED_CONS = []
        cons = rev.xpath('.//span[i[@class="icon-minus-circle"]]')
        for con in cons:
            con = con.xpath("text()").string().strip('-. ')
            if con and con not in X_CONS and con not in EXISTED_CONS:
                EXISTED_CONS.append(con)
                review.add_property(type="cons", value=con)

        excerpt = rev.xpath(".//h3[contains(., 'Beschrijving')]/following-sibling::p//text()").string(multiple=True)
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            review.ssid = review.digest() if author_name else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)