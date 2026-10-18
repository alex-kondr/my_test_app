from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.haus.de/test', force_charset='utf-8', use='curl'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[@data-sentry-component="CustomGrid"]/div')
    for cat in cats:
        name = cat.xpath('div[contains(@class, "60z25j")]/text()').string()

        subcats = cat.xpath('div/a[@data-sentry-component="Link"]')
        for subcat in subcats:
            subcat_name = subcat.xpath('text()').string()
            url = subcat.xpath('@href').string()

            if subcat_name and url:
                session.queue(Request(url, force_charset='utf-8', use='curl'), process_revlist, dict(cat=name + '|' + subcat_name))


def process_revlist(data: Response, context: dict[str, str], session: Session):

    revs_json = data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()
    try:
        revs_json = simplejson.loads(revs_json)
    except:
        revs_json = {}

    revs = revs_json.get('props', {}).get('pageProps', {}).get('data', {}).get('page', {}).get('productPages', {}).get('items', [])
    for rev in revs:
        title = rev.get('name')
        ssid = rev.get('id')
        url = 'https://www.haus.de' + rev.get('url')
        session.queue(Request(url, force_charset='utf-8', use='curl'), process_review, dict(context, title=title, ssid=ssid, url=url))

    next_url = data.xpath('(//div[@data-sentry-component="Pagination"]/a[@data-sentry-component="Link"])[last()]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8', use='curl'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.sku = str(context['ssid'])
    product.category = context['cat']

    prod_url = data.xpath('//a[regexp:test(text(), "[Zz]um Angebot")]/@href').string()
    if prod_url:
        product.url = prod_url.split('ref=as_li_tl?')[0]
    else:
        product.url = context['url']

    prod_json = data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()
    try:
        prod_json = simplejson.loads(prod_json).get('props', {}).get('pageProps', {}).get('data', {}).get('page', {})

        product.name = prod_json.get('product').get('name')
        product.ssid = prod_json.get('uuid')
        product.manufacturer = prod_json.get('product').get('shopProductData', {}).get('brand')

        mpn = prod_json.get('product').get('asinCode')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

        ean = prod_json.get('product').get('eanCode')
        if ean and ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)
    except:
        pass

    if not product.name:
        product.name = data.xpath('//div[contains(h2, "Vor- und Nachteile")]/following-sibling::div[1]/text()').string()
    if not product.name:
        product.name = context['title']

    if not product.ssid:
        product.ssid = product.sku

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[@data-sentry-component="DateTime"]/text()').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//div[contains(@data-sentry-source-file, "AuthorTeaser")]/a/text()').string()
    author_url = data.xpath('//div[contains(@data-sentry-source-file, "AuthorTeaser")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[div[@data-sentry-component="StarRating"]]/div[contains(@data-sentry-source-file, "ProductPage")]/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//tr[contains(th/text(), "Vorteile")]/td//li')
    if not pros:
        pros = data.xpath('//table[contains(.//tr/th/text(), "Vorteile")]/following-sibling::table[1]//tr[not(contains(., "Nachteile"))]//ul[@data-sentry-component="ProductProConList"]/li')

    for pro in pros:
        pro = pro.xpath('text()').string()
        if pro:
            pro = pro.lstrip(' +-.')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(th/text(), "Nachteile")]/td//li')
    for con in cons:
        con = con.xpath('text()').string()
        if con:
            con = con.lstrip(' +-.')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "html-text") and not(preceding::h2)]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//div[h2[not(preceding::div[contains(@class, "amazon-product-info")])]])[last()]/div/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[h2[not(preceding::div[contains(@class, "amazon-product-info")])]])[not(position()=last())]/div/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)