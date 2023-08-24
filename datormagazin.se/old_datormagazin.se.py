from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.datormagazin.se/kategori/artikel/tester/'), process_category, dict())


def process_category(data, context, session):
    cats = data.xpath('//div[@class="td-ss-main-content"]//node()[regexp:test(name(),"h\d")][contains(@class,"entry-title")]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_page = data.xpath('//link[@rel="next"]//@href').string()
    if next_page:
        session.queue(Request(next_page), process_category, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context['name'].split('Test:')[-1].split(':')[-1]
    product.url = context['url']
    product.category = data.xpath('//div[@class="td-post-source-tags"]//a//text()').string() or "Unknown"

    ssid = data.xpath('//article/@id').string()
    if ssid:
        product.ssid = ssid.replace('post-', '')
    else:
        product.ssid = product.url.split('/')[-2]

    review = Review()
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//span[contains(@class,"post-date")]//time/@datetime').string()
    if date:
        if 'T' in date:
            date = date.split('T')[0]
        review.date = date

    author = data.xpath('//span[contains(@class,"post-author")]//a//text()').string(multiple=True)
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@property="ratingValue"]//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=6.0))

    pros = data.xpath('(//div[@class="rwp-pros"])[1]//text()').string(multiple=True)
    if pros:
        pros = pros.split(',')
        for pro in pros:
            pro = pro.strip()
            review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[@class="rwp-cons"])[1]//text()').string(multiple=True)
    if cons:
        cons = cons.split(',')
        for con in cons:
            con = con.strip()
            review.add_property(type='cons', value=con)

    award = data.xpath('//img[contains(@src,"_rek_")]/@src').string()
    if award:
        review.add_property(type='awards', value=dict(image_src=award))

    summary = data.xpath('//div[@class="rwp-summary"][1]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class,"post-content")]/p//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary.strip(), '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)
