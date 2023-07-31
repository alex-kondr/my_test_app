from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.mixonline.com/technology/reviews'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="col-8"]')
    for prod in prods:
        context['cat'] = prod.xpath('a[@class="label-category"]/text()').string()
        context['name'] = prod.xpath('h2/text()').string()
        url = prod.xpath('a[@class="post-title"]/@href').string()
        session.queue(Request(url), process_product, dict(context, url=url))

    next_url = data.xpath('//a[@class="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_prodlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = data.xpath('//strong[contains(text(), "PRODUCT")]/following-sibling::text()[1]').string() or context['name']
    product.category = context['cat']
    product.url = data.xpath('//section[@class="entry-content"]/following-sibling::p/a/@href').string() or data.xpath('//td[strong[contains(text(), "COMPANY")]]/a/@href').string() or context['url']

    ssid = context['url'].split('-')[-1]
    try:
        int(ssid)
        product.ssid = ssid
    except ValueError:
        product.ssid = context['url'].split('/')[-1]

    manufacturer = data.xpath('//strong[contains(text(), "COMPANY")]/following-sibling::text()[1]').string()
    if manufacturer:
        product.manufacturer = manufacturer.replace(u'\u2022', '').strip()

    review = Review()
    review.type = 'pro'
    review.url = context['url']
    review.ssid = product.ssid
    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[@class="author-name"]/a/text()').string()
    if author:
        author_url = data.xpath('//p[@class="author-name"]/a/@href').string()
        review.authors.append(Person(name=author, ssid=author, url=author_url))

    summary = data.xpath('//p[@class="excerpt"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//strong[contains(text(), "PROS")]/following-sibling::text()').strings()
    for pro in pros:
        pro = pro.replace('\n', '').replace(u'\u2022', '').strip()
        if not pro:
            break
        review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//strong[contains(text(), "CONS")]/following-sibling::text()').strings()
    for con in cons:
        con = con.replace('\n', '').replace(u'\u2022', '').strip()
        review.properties.append(ReviewProperty(type='cons', value=con))

    conclusion = data.xpath('//td[strong[contains(text(), "TAKEAWAY")]]/text()').string()
    if conclusion:
        review.add_property(type='conclusion', value=conclusion.replace('“', '').replace('”', ''))

    excerpt = data.xpath('//section[@class="entry-content"]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    if excerpt or conclusion:
        product.reviews.append(review)
        session.emit(product)
