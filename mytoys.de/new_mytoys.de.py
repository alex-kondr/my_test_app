from agent import *
from models.products import *
import simplejson


XCAT = ['Inspiration', 'Marken', '%Sale%', '% Sale', 'Aktionen', 'Neuheiten', 'Beratung', 'Inspiration & Themen', 'Premium-Marken', "Levi's®", 'Tommy Hilfiger', 'Nachhaltige Artikel', 'adidas', 'Nike', 'LeGer Home by Lena Gercke', '']


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
    session.queue(Request('https://www.otto.de/', use='curl', force_charset='utf-8'), process_frontpage, dict())
    session.queue(Request('https://www.otto.de/damen/', use='curl', force_charset='utf-8'), process_catlist, dict(cat='Damen'))


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "global-navigation")]/li[contains(@class, "item-element")]//a')
    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_catlist, dict(cat=name))


def process_catlist(data,context, session):
    strip_namespace(data)

    cats = data.xpath('//div[@class="nav_local-category"]')
    for cat in cats:
        name = cat.xpath('.//li[@class="nav_local-link nav_link-headline"]/a/span[@class="nav_link-title"]/text()').string()

        if name and name not in XCAT:
            sub_cats = cat.xpath('.//li[@class="nav_local-link "]/a')
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('span[@class="nav_link-title"]/text()').string()
                url = sub_cat.xpath('@href').string()

                if not sub_name.lower().startswith('alle'):
                    if '/?' in url:
                        session.queue(Request(url + '&sortiertnach=bewertung', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name, cat_url=url))
                        session.queue(Request(url + '?sortiertnach=bewertung', use='curl', force_charset='utf-8'), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name, cat_url=url))


def process_prodlist(data, context, session):
    strip_namespace(data)

    prods = data.xpath('//article[contains(@class, "product")]')
    for prod in prods:
        name = prod.xpath('.//p[contains(@class, "find_tile__name")]/text()').string()
        url = prod.xpath('.//a/@href').string()

        prod_json = prod.xpath('.//script[@type="application/ld+json"]/text()').string()
        if prod_json:
            revs_cnt = simplejson.loads(prod_json).get('aggregateRating', {}).get('reviewCount')
            if revs_cnt and int(revs_cnt) > 0:
                session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(name=name, url=url))
        else:
            return

    prods_cnt = data.xpath('//span[contains(@class, "itemCount")]/text()').string()
    if prods_cnt:
        prods_cnt = int(prods_cnt.replace('Produkte', '').replace('.', '').strip())
        '&l=gp&o=120&sortiertnach=bewertung'
    next_url = data.xpath('//a[span[@class="next-link"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_prodlist, dict())


def process_product(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//text()').string()
    author_url = data.xpath('/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
