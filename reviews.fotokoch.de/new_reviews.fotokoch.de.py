from agent import *
from models.products import *


XCAT = ['Second Hand', 'AREA', 'Aktionen %', 'Workshops', 'Blog', 'Geschenkgutscheine', 'alle', 'Angebote']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.fotokoch.de/index.html', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[contains(@class, "checkboxhack_nav_more item_") and div[contains(@class, "checkboxhack_nav_more")]]')
    for cat in cats:
        name = cat.xpath('span[@class="nav_backward"]/span/text()').string()

        if name not in XCAT:
            sub_cats = cat.xpath('div[contains(@class, "checkboxhack_nav_more")]')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('span[@class="nav_backward"]/span/text()').string()
                url = sub_cat.xpath('a[@class="nav_desktop_level_2 navi"]/@href').string()

                if sub_name and sub_name not in XCAT:
                    sub_name = sub_name.replace('Weitere ', '').title()
                    session.queue(Request(url, force_charset='utf-8'), process_catlist, dict(cat=name + '|' + sub_name))


def process_catlist(data, context, session):
    subcats = data.xpath('//div[@id="level_seitenmenu"]/a')
    for subcat in subcats:
        subcat_name = subcat.xpath('text()').string().replace('von ', '').replace('für ', '').strip()
        url = subcat.xpath('@href').string()

        if subcat_name not in XCAT:
            session.queue(Request(url + '?listenlimit=0,50', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "product-item")]')
    for prod in prods:
        name = prod.xpath('.//h2[@class="product-grid-title"]/text()').string()
        url = prod.xpath('.//a[@class="interaction"]/@href').string()

        revs_cnt = prod.xpath('.//span[@class="anzahl"]/text()').string()
        if revs_cnt and int(revs_cnt.strip('()')) > 0:
            session.queue(Request(url, force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@name="artikelnr"]/@value').string()
    product.sku = product.ssid
    product.category = context['cat'].replace('nach Marke|', '|').replace('Nach Marke|', '|').replace('||', '|')

    prod_info = data.xpath('//script[@type="application/ld+json"]/text()').string()
    if prod_info:
        product.manufacturer = prod_info.replace('\t', '').replace('\n', '').split('"Brand", "name": "')[-1].split('" },')[0]

    mpn = data.xpath('//div[@itemprop="mpn"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//div[@class="table-row" and contains(., "EAN")]/div[@class="_td last"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 11:
        product.add_property(type='id.ean', value=ean)

    session.do(Request(product.url.replace('.html', '_bewertungen.html'), force_charset='utf-8'), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="bewertungsliste-item"]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('.//input[@name="bewertungid"]/@value').string()

        date_author = rev.xpath('.//div[@class="from"]/text()').string()
        if date_author:
            review.date = date_author.split(' am ')[-1].split()[0]

            author = date_author.replace('von ', '').split()[0]
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="hidden-sterne"]/@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.strip(' width:%;')) / 20
            if grade_overall > 0:
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        is_recommended = rev.xpath('.//div[contains(., "Ich kann dieses Produkt weiterempfehlen!")]/text()').string()
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev.xpath('.//div[@class="hilfreich" and contains(., "Person fand diese Bewertung hilfreich")]/text()').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes.split()[0])
            if hlp_yes > 0:
                review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.xpath('.//div[@class="hilfreich" and contains(., "Person fand diese Bewertung nicht hilfreich")]/text()').string()
        if hlp_no:
            hlp_no = int(hlp_no.split()[0])
            if hlp_no > 0:
                review.add_property(type='not_helpful_votes', value=hlp_no)

        title = rev.xpath('.//div[regexp:test(@class, "^titel")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[@class="text"]//text()').string(multiple=True)
        if excerpt and len(excerpt.strip(' \n\t+-.')) > 2:
            review.title = title.strip(' \n\t+-.')
        else:
            excerpt = title

        if excerpt:
            excerpt = excerpt.strip(' \n\t+-.')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
