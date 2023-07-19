import simplejson

from agent import *
from models.products import *


URL = 'https://www.thegnet.org/blog-frontend-adapter-public/v1/post-list-widget/render-model?timezone=Europe/Zurich&postLimit=500&categoryId=87c39d34-b1fa-4ed1-abfe-580cd4b663bb'
OPTIONS = "--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'instance: UINFp_WrkC1phy2kw2TUJrqfBDIO5sDGMFM2WEq9ab4.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTE5VDA3OjU0OjU2Ljc1MVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiI2MjJkNjU4My0wZGE4LTRlMTYtOGExZi04OWYyMGJmYTM0M2MiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ' -H 'Authorization: UINFp_WrkC1phy2kw2TUJrqfBDIO5sDGMFM2WEq9ab4.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTE5VDA3OjU0OjU2Ljc1MVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiI2MjJkNjU4My0wZGE4LTRlMTYtOGExZi04OWYyMGJmYTM0M2MiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ' -H 'locale: de' -H 'x-wix-site-revision: 1365' -H 'Alt-Used: www.thegnet.org' -H 'Connection: keep-alive' -H 'Referer: https://www.thegnet.org/_partials/wix-thunderbolt/dist/clientWorker.eff8282f.bundle.min.js' -H 'Cookie: XSRF-TOKEN=1689746193|YpIwqZ6caWmw; hs=-654853905; svSession=f49c23e81742e05e44ea43a5e8fafac4c70b36fabd861c2995f6c3db10edcdb444a8f30472458a8d2f101dd34dd1a0391e60994d53964e647acf431e4f798bcdd0a36ed5f39d45fdf53266adf3d494fcd7dbeccf0e619422a235d4ee8e4323c21a508a29975c3450b028d6050d90b2bb8be7a04159f6f51bcb87c592caaff315a11d4ec13a2f94353ece99ae8a1ce191' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'TE: trailers'"


def run(context, session):
    session.queue(Request(URL, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = simplejson.loads(data.content).get('posts', {}).get('body', [])
    for prod in prods:
        name = prod.get('title', '').replace('im Test', '').replace(u'\u2019', "'").split(':', 1)
        name = name[1].strip() if len(name) > 1 else name[0].strip()

        url = prod.get('link')
        session.queue(Request(url), process_product, dict(name=name, url=url))


def process_product(data, context, session):
    prod_json = data.xpath('//script[@type="application/ld+json"]/text()').string()
    author_url = ''
    date = ''
    if prod_json:
        prod_json = simplejson.loads(prod_json)
        author_url = prod_json.get('author', {}).get('url')
        date = prod_json.get('datePublished', '').split('T')[0]
        
    product = Product()
    product.name = context['name']
    product.url = data.xpath('//span[contains(@class, "public-DraftStyleDefault-ltr")]//a/@href').string() or context['url']
    product.ssid = context['url'].split('/')[-1]
    product.category = 'review'

    review = Review()
    review.type = 'pro'
    review.ssid = product.ssid
    review.url = context['url']
    
    if date:
        review.date = date 
    else:
        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

    title = data.xpath('//div[@data-id="rich-content-viewer"]//p[@id="viewer-foo"]//text()').string()
    if title:
        review.title = title.replace(u'\u201c', '"').replace(u'\xf6', 'o').replace(u'\xfc', 'u').replace(u'\u201d', '"').replace(u'\xe4', 'a').replace(u'\xc4', 'A').replace(u'\xdc', 'U').replace(u'\u2026', '...')
    
    author = data.xpath('//meta[@property="article:author"]/@content').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt_conclusion = data.xpath('//div[@data-id="rich-content-viewer"]//text()').string(multiple=True)
    if excerpt_conclusion:
        excerpt_conclusion = excerpt_conclusion.replace(u'\u201c', '"').replace(u'\xf6', 'o').replace(u'\xfc', 'u').replace(u'\u201d', '"').replace(u'\xe4', 'a').replace(u'\xc4', 'A').replace(u'\xdc', 'U').replace(u'\u2026', '...').split('Fazit:')

        if len(excerpt_conclusion) > 1:
            conclusion = excerpt_conclusion[1].strip()
            review.add_property(type='conclusion', value=conclusion)    

        excerpt = excerpt_conclusion[0]
        if title:
            excerpt = excerpt.replace(title, '').strip()
        review.add_property(type='excerpt', value=excerpt)

        review.ssid = product.ssid

        product.reviews.append(review)        

    if product.reviews:
        session.emit(product)
