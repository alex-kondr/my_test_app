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
    session.queue(Request('http://www.olcsobbat.hu/', use='curl', force_charset='utf-8'), process_frontpage, dict())
    session.queue(Request('https://www.olcsobbat.hu/ruhazat_kellekek/?order_by=ertekeles', use='curl', force_charset='utf-8'), process_prodlist, dict(cat='Divat és ruházat'))


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="menu"]/li')
    for cat in cats:
        name = cat.xpath('span/a/text()').string()

        sub_cats = cat.xpath('.//div[@class="col-sm-2"]')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div[@class="title"]/text()').string()

            sub_cats1 = sub_cat.xpath('.//li/a')
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.xpath('text()').string()
                url = sub_cat1.xpath('@href').string()
                session.queue(Request(url + '?order_by=ertekeles', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))



def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//div[@class="datasheetListWidget list"]/div')
    for prod in prods:
        name = prod.xpath('.//h2/a/text()').string()
        url = prod.xpath('.//h2/a/@href').string()

        rating = prod.xpath('.//span[@class="ratingWidget"]')
        if rating:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))
        else:
            return

    next_page = data.xpath('//link[@rel="next"]/@href').string()
    if next_page:
        session.queue(Request(url + '&order_by=ertekeles', use='curl', force_charset='utf-8'), process_prodlist, dict(context))


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].split('-')[-1]
    product.category = context['cat']
    product.manufacturer = data.xpath('//span[@itemprop="brand"]/meta/@content').string()

    mpn = data.xpath('//div[@class="articleIdDesktop"]/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin"]/@content').string()
    if ean:
        ean = ean.split(',')[0].strip()
        if ean.isdigit() and len(ean) > 10:
            product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@class="review" and @id and div[@class="row"]]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@id').string().split('_')[-1]
        review.date = rev.xpath('.//meta[@itemprop="datePublished"]/@content').string()

        author = rev.xpath('.//div[@class="author"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//span[@class="ratingWidget"]/@title').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Értékelés:', '').replace('csillag', '')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified_buyer = rev.xpath('.//img[contains(@src, "review-authentic")]')
        if is_verified_buyer:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.xpath('.//span[span[contains(@class, "thumbs-up")]]/text()').string(multiple=True)
        if hlp_yes and int(hlp_yes.strip('( )')) > 0:
            hlp_yes = int(hlp_yes.strip('( )'))
            review.add_property(type='helpful_votes', value=hlp_yes)

        hlp_no = rev.xpath('.//span[span[contains(@class, "thumbs-down")]]/text()').string(multiple=True)
        if hlp_no and int(hlp_no.strip('( )')) > 0:
            hlp_no = int(hlp_no.strip('( )'))
            review.add_property(type='not_helpful_votes', value=hlp_no)

        excerpt = rev.xpath('.//p[@itemprop="reviewBody"]//text()').string(multiple=True)
        if excerpt:
            excerpt = excerpt.strip(' +-')
            if len(excerpt) > 2:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    if product.reviews:
        session.emit(product)

# no next_page
