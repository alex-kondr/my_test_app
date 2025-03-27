from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.coolgadget.de/', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data,context, session):
    cats = data.xpath('//a[contains(@class, "category-link")]')
    for cat in cats:
        name = cat.xpath('text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//li[contains(@class, "level-2")]/a[contains(@class, "item-link")]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('span[contains(@class, "title")]/text()').string()
        url = sub_cat.xpath('@href').string()
        session.queue(Request(url + '?items=100'), process_prodlist, dict(cat=context['cat'] + '|' + sub_name))

    if sub_cats:
        return

    cats = data.xpath('//a[contains(@class, "item-link")]')
    for cat in cats:
        name = cat.xpath('span[contains(@class, "title")]/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_catlist, dict(cat=context['cat'] + '|' + name))


def process_prodlist(data, context, session):
    prods = data.xpath('//body/div[@data-id="ALT.ItemThumbnail"]')
    for prod in prods:
        name = prod.xpath('div[contains(@class, "title")]/a/text()').string()
        url = prod.xpath('div[contains(@class, "title")]/a/@href').string()

        revs_cnt = prod.xpath('.//span[@class="count"]/text()').string()
        if revs_cnt and int(revs_cnt) > 0:
            session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//li[contains(@class, "next-page")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
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
    session.do(Reuqest(revs_url), process_reviews, dict(product=product, url=revs_url))


def process_reviews(data,context, session):
    product = context['product']

    revs = data.xpath('//div[@data-refresh-id]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = context['url']
        review.ssid = rev.xpath('@data-review-id').string()

        date_author = rev.spath('.//div[contains(@class, "author")]/text()').string()
        if date_author:
            review.date = date_author.rsplit(' ', 1)[0].split()[-1]

            author = date_author.split(' verfasst ')[0]
            review.authors.append(Person(name=author, ssid=author))

        is_verified_buyer = rev.xpath('.//span[contains(., "Verifizierter Kauf")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes_no = rev.xpath('.//small[@class="grey"]/text()').string()
        if hlp_yes:
            hlp_yes = int(hlp_yes_no.split(' von ')[0])
            hlp_no = int(hlp_yes_no.split(' von ')[1])

            if hlp_yes > 0:
                review.add_property(type='helpful_votes', value=hlp_yes)

            if hlp_no > 0:
                review.add_property(type='not_helpful_votes', value=hlp_no)

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
