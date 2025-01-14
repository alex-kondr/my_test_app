import simplejson

from agent import *
from models.products import *


URL = 'https://www.thegnet.org/blog-frontend-adapter-public/v1/post-list-widget/render-model?timezone=Europe/Zurich&postLimit=500&categoryId=87c39d34-b1fa-4ed1-abfe-580cd4b663bb'
OPTIONS = "-H 'instance: u9PwPO9zmtAD-O9CjKKkgFWRcUJXeFC9TJK0oH3_XNY.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTI5VDIxOjMyOjIxLjg1MloiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiIzNzUwYzRhZC04YTEyLTQ2MzItYThmZi0zZDFjMDMzYjZkNzMiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ'"


def run(context, session):
    session.queue(Request(URL, use='curl', options=OPTIONS, max_age=0, force_charset='utf-8'), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = simplejson.loads(data.content).get('posts', {}).get('body', [])

    for prod in prods:
        name = prod.get('title', '').replace('im Test', '').replace('The(G)net Review - ', '').split(':', 1)
        name = name[1].strip() if len(name) > 1 else name[0].strip()
        url = prod.get('link')
        session.queue(Request(url, use='curl', max_age=0, force_charset='utf-8'), process_product, dict(name=name, url=url))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.ssid = context['url'].split('/')[-1]

    category = ''
    categories = data.xpath('//a[@data-hook="category-label-list__item"]')
    for cat in categories:
        cat = cat.xpath('text()').string()
        if 'Reviews' not in cat:
            category += '/' + cat
    if category:
        product.category = 'Games|' + category[1:]

    product.url = data.xpath('//span[contains(@class, "public-DraftStyleDefault-ltr")]//a/@href').string()
    if not product.url or 'thegnet.org' in product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.ssid = product.ssid
    review.url = context['url']
    review.title = data.xpath('//title/text()').string()

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    summary = data.xpath('//div[@data-id="rich-content-viewer"]//p[@id="viewer-foo"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    author = data.xpath('//meta[@property="article:author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = ''
    conclusion = ''
    is_conclusion = False
    excerpt_conclusion = data.xpath('//div[@data-id="rich-content-viewer"]/div/*[not(@id="viewer-foo")]')
    for exc_con in excerpt_conclusion:
        grade_img = exc_con.xpath('.//div[@style="--dim-height:658;--dim-width:1920"]/@class').string()
        if grade_img:
            break

        text = exc_con.xpath('.//span[not(@class)]//text()').string(multiple=True)
        if text:
            if 'Fazit:' in text or is_conclusion:
                is_conclusion = True
                conclusion += ' ' + text
            else:
                excerpt += ' ' + text

    if conclusion:
        conclusion = conclusion.replace('Fazit:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt.strip())

    if excerpt or conclusion:
        product.reviews.append(review)

        session.emit(product)
