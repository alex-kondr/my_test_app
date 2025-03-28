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
    session.queue(Request('https://www.coolgadget.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data,context, session):
    strip_namespace(data)
    cats = data.xpath('//a[contains(@class, "category-link")]')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[contains(@class, "level-1")]/a[contains(@class, "item-link")]')
    for cat in cats:
        name = cat.xpath('span[contains(@class, "title")]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_subcatlist, dict(cat=context['cat'] + '|' + name))


def process_subcatlist(data, context, session):
    strip_namespace(data)
    sub_cats = data.xpath('//li[contains(@class, "level-2")]/a[contains(@class, "item-link")]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('span[contains(@class, "title")]/text()').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url + '?items=100', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//article[contains(@class, "item")]/div[@data-id]')
    for prod in prods:
        name = prod.xpath('div[contains(@class, "title")]/a/text()').string()
        url = prod.xpath('div[contains(@class, "title")]/a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="count"]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//li[contains(@class, "next-page")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//input[@id="ArticleId"]/@value').string()
    product.sku = data.xpath('//span[@itemprop="sku"]/text()').string()
    product.category = context['cat'].replace('weitere Modelle', '').replace('||', '|').strip()
    product.manufacturer = data.xpath('(//label[contains(., "Marke")]/following-sibling::span)[1]/text()').string()

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin"]/@content').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    revs_url = data.xpath('//div[contains(@class, "show-all-reviews")]/a/@href').string()
    session.do(Request(revs_url, use='curl', force_charset='utf-8'), process_reviews, dict(product=product, url=revs_url))


def process_reviews(data,context, session):
    strip_namespace(data)

    product = context['product']

    revs = data.xpath('//div[@data-refresh-id]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.ssid = rev.xpath('@data-review-id').string()

        date_author = rev.xpath('.//div[contains(@class, "author")]/text()').string(multiple=True)
        if date_author:
            review.date = date_author.rsplit(' ', 1)[0].split()[-1]

            author = date_author.split(' verfasst ')[0]
            review.authors.append(Person(name=author, ssid=author))

        is_verified_buyer = rev.xpath('.//span[contains(., "Verifizierter Kauf")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes_no = rev.xpath('.//small[@class="grey"]/text()').string()
        if hlp_yes_no:
            hlp_yes = hlp_yes_no.split(' von ')[0]
            hlp_no = hlp_yes_no.split(' von ')[1].split()[0]

            if hlp_yes and hlp_yes.isdigit() and int(hlp_yes) > 0:
                review.add_property(type='helpful_votes', value=int(hlp_yes))

            if hlp_no and hlp_no.isdigit() and int(hlp_no) > 0:
                review.add_property(type='not_helpful_votes', value=int(hlp_no))

        title = rev.xpath('.//h4[contains(@class, "item-title")]//text()').string(multiple=True)
        excerpt = rev.xpath('.//div[contains(@class, "item-comment")]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next page
