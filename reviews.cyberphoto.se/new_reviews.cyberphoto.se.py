from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cyberphoto.se/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats_json = data.xpath('//div[@id="navigation-mobile"]/text()').string()
    if cats_json:
        cats = simplejson.loads(cats_json).get('mobileContentLinks', [{}])[0].get('links', [])

        for cat in cats:
            name = cat.get('name')

            sub_cats = cat.get('links', [])
            for sub_cat in sub_cats:
                sub_name = sub_cat.get('name')
                url = sub_cat.get('url')
                session.queue(Request('https://www.cyberphoto.se' + url), process_prodlist, dict(cat='Foto & Video|' + name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[contains(@class, "overflow-y-hidden")]')
    for prod in prods:
        name = prod.xpath('a/text()').string()
        manufacturer = prod.xpath('div[contains(@class, "text-sm")]/text()').string()
        url = prod.xpath('a/@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, manufacturer=manufacturer, url=url))

    next_url = data.xpath('//a[contains(., "Ladda fler")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    product.manufacturer = context['manufacturer']
    product.sku = data.xpath('//div[@id="videoly-product-id"]/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//p[contains(.,'Testad av')]//text()").string(multiple=True)
    if date:
        review.date = date.split()[-1].strip(' .')

    author = data.xpath("//p[contains(.,'Testad av')]//text()").string(multiple=True)
    if author:
        author = author.split()[-2].strip()
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//p[contains(., "Betyg 1-10:")]/following-sibling::ul[1]/li')
    for grade in grades:
        grade_name, grade_val = grade.xpath('.//text()').string().split()
        grade_val = float(grade_val.replace(',', '.'))
        review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    img_aw = data.xpath("//img[contains(@src,'120x120guld_SE.png')]/@src").string()
    if img_aw:
        product.add_property(type='awards', value={'name': 'Toppklass', 'image_src': img_aw})

    pros = data.xpath('(//p[b[text()="Plus"]])[1]/text()')
    for pro in pros:
        pro = pro.string().strip(' +-')
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[b[text()="Minus"]])[1]/text()')
    for con in cons:
        con = con.string().strip(' +-')
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//p[b[text()="Slutsats"]])[1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('Slutsats', '').strip()
        review.add_property(type='conclsuion', value=conclusion)

    excerpt = data.xpath('(//p[b[text()="Plus"]])[1]/preceding-sibling::p[not(i)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p[b[text()="Minus"]])[1]/preceding-sibling::p[not(i)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p[b[text()="Slutsats"]])[1]/preceding-sibling::p[not(i)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p[contains(., "Testad av")])[1]/preceding-sibling::p[not(i)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="editor-string text-md"]/p[not(contains(., "Plus") or contains(., "Minus") or contains(., "Slutsats") or contains(., "Testad av") or i)]//text()').string(multiple=True)

    if excerpt:
        review.ad_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
