from agent import *
from models.products import *
import simplejson


XCAT = ['PC GROSBILL & CONFIG SUR MESURE', 'VENTES FLASH & BONS PLANS', 'PC reconditionnés', 'Composants reconditionnés', 'Stockages reconditionnés', 'Réseaux reconditionnés', 'Périphériques reconditionnés', 'Gaming reconditionné', 'Nos bons plans', 'Les Soldes Grosbill']


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
    session.queue(Request('https://www.grosbill.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "menu-hori")]')
    for cat in cats:
        name = cat.xpath('label//p//text()').string(multiple=True).strip()

        if name not in XCAT:
            cats1 = cat.xpath('div[@class="sous_level"]//ul[contains(@class, "grb_menu")]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('li[@class]//span/text()').string()

                if cat1_name not in XCAT:
                    subcats = cat1.xpath('li[not(@class)]/a')
                    for subcat in subcats:
                        subcat_name = subcat.xpath('span/text()').string()
                        url = subcat.xpath('@href').string().strip('+')

                        if 'tous les' in subcat_name.lower():
                            subcat_name = ''

                        session.queue(Request(url, use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//a[@class="prod_txt_left"]')
    for prod in prods:
        name = prod.xpath('.//p[contains(@class, "libelle")]//text()').string(multiple=True)
        url = prod.xpath('@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "nbr_avis")]/p/text()').string()
        if revs_cnt:
            revs_cnt = revs_cnt.replace('avis', '').strip('( )')
            if revs_cnt and int(revs_cnt) > 0:
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.aspx', '')
    product.sku = data.xpath('//p[contains(@id, "lbl_num_produit")]/text()').string()
    product.category = context['cat'].strip(' |')
    product.manufacturer = data.xpath('//meta[@property="product:brand"]/@content').string()

    mpn = data.xpath('//p[contains(@id, "lbl_ref_constructeur")]/text()').string()
    if mpn:
        mpn = mpn.rstrip('* ')
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//p[contains(@id, "code_ean")]/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[contains(@class, "page__review-item")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        author = rev.xpath('.//p[@class="un_avis__nom"]/text()').string()
        if author:
            if 'anonymous' not in author.lower():
                review.authors.append(Person(name=author, ssid=author))
            else:
                author = None

        grade_overall = rev.xpath('.//span[contains(@class, "note")]/text()').string()
        if grade_overall:
            grade_overall = float(grade_overall.split('/')[0].strip('( )'))
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        excerpt = rev.xpath('.//p[contains(@class, "commentaire")]/text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip(' .?"')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                review.ssid = review.digest() if author else review.digest(excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

    # Loaded all revs
