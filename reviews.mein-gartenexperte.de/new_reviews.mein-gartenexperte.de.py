from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mein-gartenexperte.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "submenu index category")]')
    for cat in cats:
        name = cat.xpath('a/text()').string()

        sub_cats = cat.xpath('ul[@class="level_2"]/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('a/text()').string()

            sub_cats1 = sub_cat.xpath('ul[@class="level_3"]/li/a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string()
                    url = sub_cat1.xpath('@href').string()
                    session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('a/@href').string()
                session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    revs_json = data.xpath('//script[contains(., "window.products")]/text()').string()
    if revs_json:
        
        print(revs_json.replace('window.products=', '').replace('="', '=\\"').replace('"\'', '\\""').replace('\'<', '"<').replace('" ', '\\" ').replace('">', '\\">').replace("'", '"').replace(',}', '}').replace(',]', ']').replace('G 3/4\\"",', '').replace('"<b', '\\"<b').replace('/2":', '/2\\":').replace('/4":', '/4\\":').replace(' "', ' \\"').replace('"-', '\\"-'))
        
        revs = simplejson.loads(revs_json.replace('window.products=', ''))#.replace('="', '=\\"').replace('"\'', '\\""').replace('\'<', '"<').replace('" ', '\\" ').replace('">', '\\">').replace("'", '"').replace(',}', '}').replace(',]', ']').replace('G 3/4\\"",', '').replace('"<b', '\\"<b').replace('/2":', '/2\\":').replace('/4":', '/4\\":').replace(' "', ' \\"').replace('"-', '\\"-'))
        for rev in revs:
            product = Product()
            product.name = rev.get('titel')
            product.ssid = rev.get('id')
            product.sku = product.ssid
            product.category = context['cat']
            product.manufacturer = rev.get('hersteller')

            url = rev.get('berichtButton')
            if url:
                url = 'https://www.mein-gartenexperte.de/' + url
                session.queue(Request(url), process_review, dict(product=product, url=url))


def process_review(data, context, session):
    product = context['product']

    product.url = data.xpath('//a[contains(., "Zu Amazon")]/@href').string()
    if not product.url:
        product.url = context['url']

    mpn = data.xpath('//meta[@itemprop="mpn"]/@content').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//div[@class="content-text media media--left"]/h1/text()').string()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
         review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "author")]//span[@class="h4"]/text()').string()
    author_url = data.xpath('//div[contains(@class, "author")]//span[@class="h4"]/text()').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//meta[@itemprop="ratingValue"]/@content').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//ul[@class="pros"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="cons"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="rating ce_product"]/div[@itemprop="description"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)


    excerpt = data.xpath('//div[contains(@class, "content-text")]//p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
