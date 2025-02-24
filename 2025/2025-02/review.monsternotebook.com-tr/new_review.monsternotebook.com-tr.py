from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.monsternotebook.com.tr/laptop/'), process_catlist, dict(cat='Laptoplar'))
    session.queue(Request('https://www.monsternotebook.com.tr/masaustu-bilgisayarlar/'), process_catlist, dict(cat='Masaüstü Bilgisayarlar'))
    session.queue(Request('https://www.monsternotebook.com.tr/aksesuarlar/'), process_catlist, dict(cat='Aksesuarlar'))


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="pt-10 pb-10 ps-15"]')
    for cat in cats:
        name = cat.xpath('div/a/text()').string().split(' (')[0]

        sub_cats = cat.xpath('ul/li')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('div/a/text()').string().split(' (')[0]

            sub_cats1 = sub_cat.xpath('ul/li//a')
            if sub_cats1:
                for sub_cat1 in sub_cats1:
                    sub_name1 = sub_cat1.xpath('text()').string().split(' (')[0]
                    url = sub_cat1.xpath('@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name + '|' + sub_name1))
            else:
                url = sub_cat.xpath('div/a/@href').string()
                session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "card border-gray")]')
    for prod in prods:
        name = prod.xpath('.//img[@class="card-img img-fluid"]/@alt').string()
        url = prod.xpath('a[@class="stretched-link"]/@href').string()

        revs_cnt = prod.xpath('.//div[contains(@class, "text-secondary")]/text()').string()
        if revs_cnt:
            revs_cnt = int(revs_cnt.split()[-1].strip('()'))
            if revs_cnt > 0:
                session.do(Request(url), process_product, dict(context, name=name, url=url, revs_cnt=revs_cnt))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-product-id').string()
    product.sku = product.ssid
    product.category = context['cat']
    product.manufacturer = 'Monster Notebook'

    mpn = data.xpath('//div/@data-sku').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//li[div[contains(., "Ürün Kodu")]]//span[@class="me-10"]/text()').string()
    if ean and ean.isdigit() and len(ean) > 10:
        product.add_property(type='id.ean', value=ean)

    context['product'] = product

    process_reviews(data, context, session)


def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[contains(@class, "user-comment")]')
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = rev.xpath('@data-id').string()
        review.date = rev.xpath('.//div[contains(@class, "border-left-gray-new")]/text()').string()

        author = rev.xpath('.//div[@class="fs-14 text-light pe-5"]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('.//div[@class="card-rating-current"]/@style').string()
        if grade_overall:
            grade_overall = grade_overall.split()[-1].replace(';', '')
            if grade_overall.isdigit() and float(grade_overall) > 0:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        help_yes = rev.xpath('.//a[@rel="positive"]/span/text()').string()
        if help_yes and help_yes.isdigit() and int(help_yes) > 0:
            review.add_property(type='helpful_votes', value=int(help_yes))

        help_no = rev.xpath('.//a[@rel="negative"]/span/text()').string()
        if help_no and help_no.isdigit() and int(help_yes) > 0:
            review.add_property(type='not_helpful_votes', value=int(help_no))

        title = rev.xpath('.//div[@class="fs-16 mb-4"]//text()').string(multiple=True)
        excerpt = rev.xpath('.//p[@data-fulltext]//text()').string(multiple=True)
        if excerpt:
            review.title = title
        else:
            excerpt = title

        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    offset = context.get('offset', 0) + 6
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        tags = context.get('tags', data.xpath('//div/@data-tags').string().split('|'))
        parameters = simplejson.dumps(dict(
            ExternalId=product.ssid,
            ContentTypeId="82",
            PageSize="6",
            CurrentPage=str(next_page),
            Tags=tags
        ))
        next_url = 'https://www.monsternotebook.com.tr/tr/Widget/Get/ProductComments?parameters=' + parameters
        session.do(Request(next_url), process_reviews, dict(context, product=product, offset=offset, page=next_page, tags=tags))

    elif product.reviews:
        session.emit(product)
