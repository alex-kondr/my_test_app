from agent import *
from models.products import *


XCAT = ['Angebote', 'Gutscheine']


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
    session.queue(Request('https://www.dehner.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('(//ul[@class="splide__list" and li/a])[1]/li/a')
    for cat in cats:
        name = cat.xpath('.//p/text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    subcats = data.xpath('//div[contains(div/text(), "Alle Kategorien")]/div/a')
    for subcat in subcats:
        subcat_name = subcat.xpath('text()').string()
        url = subcat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(cat=context['cat']+'|'+subcat_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//h5/a[contains(@class, "product-card__link")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@aria-label="Go to next page"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url'].split('?')[0]
    product.ssid = context['url'].split('=')[-1]
    product.sku = product.ssid
    product.category = context['cat']

    manufacturer = data.xpath('//img[contains(@alt, "Markenlogo")]/@src').string()
    if manufacturer:
        product.manufacturer = manufacturer.split('/')[-1].split('?')[0].title()

    revs = data.xpath('//div[contains(div/h4, "Produktbewertungen")]/div[p]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url

        date = rev.xpath('.//p[contains(@class, "MuiTypography-copyRegular") and contains(text(), "T")]/text()').string()
        if date:
            review.date = date.split('T')[0]

        author = rev.xpath('.//p[contains(@class, "MuiTypography-copyBold") and not(contains(., "Anonym"))]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[contains(@aria-label, "Stars")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Stars', '')
            if grade_overall and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        title = rev.xpath('.//p[contains(@class, "MuiTypography-copyRegular")]/span/text()').string()
        excerpt = rev.xpath('.//p[contains(@class, "MuiTypography-copyRegular") and span]/text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt and len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            review.ssid = review.digest() if author else review.digest(excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
