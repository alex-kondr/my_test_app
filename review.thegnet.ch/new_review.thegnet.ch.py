import simplejson

from agent import *
from models.products import *


URL = 'https://www.thegnet.org/blog-frontend-adapter-public/v1/post-list-widget/render-model?timezone=Europe/Zurich&postLimit=500&categoryId=87c39d34-b1fa-4ed1-abfe-580cd4b663bb'
OPTIONS = "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'instance: PDqMOJP-sGwXC78TNeunt9IodrWqlVoBahKmqLCPN6s.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTE4VDE5OjMyOjUzLjMwNVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiIzNzUwYzRhZC04YTEyLTQ2MzItYThmZi0zZDFjMDMzYjZkNzMiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ' -H 'Authorization: PDqMOJP-sGwXC78TNeunt9IodrWqlVoBahKmqLCPN6s.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIzLTA3LTE4VDE5OjMyOjUzLjMwNVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiIzNzUwYzRhZC04YTEyLTQ2MzItYThmZi0zZDFjMDMzYjZkNzMiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ' -H 'locale: de' -H 'x-wix-site-revision: 1365' -H 'Connection: keep-alive' -H 'Referer: https://www.thegnet.org/_partials/wix-thunderbolt/dist/clientWorker.eff8282f.bundle.min.js' -H 'Cookie: XSRF-TOKEN=1689706516|oA2nDVaAINdl; hs=1164313749; svSession=6d788d220fd6d83e43a0d2b35b098311c9219fbe73fe1b797e4384c464573b8040e0e254acfb07bc0447ca270c0d23af1e60994d53964e647acf431e4f798bcd7a4e12d043436c63815a0fe37fd12761409138840b715a3ac350827f606c6b761a508a29975c3450b028d6050d90b2bb8be7a04159f6f51bcb87c592caaff315a11d4ec13a2f94353ece99ae8a1ce191' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'TE: trailers'"

def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request(URL, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict())
    
    
def process_prodlist(data, context, session):
    prods = simplejson.loads(data.content).get('posts', {}).get('body', [])
    for prod in prods:
        name = prod.get('title', '').replace('im Test', '').replace(u'\u2019', "'").split(':', 1)
        name = name[1].strip() if len(name) > 1 else name[0].strip()

        url = prod.get('link')
        session.queue(Request(url), process_product, dict(name=name, url=url))



def process_product(data, context, session):
    prod_json = simplejson.loads(data.xpath('//script[@type="application/ld+json"]/text()').string())
    
    product = Product()
    product.name = context['name']
    product.ulr = context['url']
    product.ssid = context['url'].split('/')[-1]
    
    review = Review()
    review.type = 'pro'
    review.ssid = product.ssid
    review.date = prod_json.get('datePublished', '').split('T')[0]
    
    author = prod_json.get('author', {}).get('name')
    author_url = prod_json.get('author', {}).get('url')
    if author:
        review.authors.append(Person(name=author, ssid=author, url=author_url))
        
    # for con in data.xpath("//strong[contains(text(), 'Negativ')]//parent::p//following-sibling::p"):
    #     if con.xpath(".//strong"):
    #         break
    #     if con:
    #         con = con.xpath("text()").string()
    #         review.properties.append(ReviewProperty(type='cons', value=con))

    # for pro in data.xpath("//strong[contains(text(), 'Positiv')]//parent::p//following-sibling::p"):
    #     if pro.xpath(".//strong"):
    #         break
    #     if pro:
    #         pro = pro.xpath("text()").string()
    #         review.properties.append(ReviewProperty(type='pros', value=pro))
        
    exceprt_conclusion = data.xpath('//div[@data-id="rich-content-viewer"]//text()').string(multiple=True).split('Fazit')
    
    if len(excerpt) > 1:
        conclusion = exceprt_conclusion[1]
        review.add_property(type='conclusion', value=conclusion)
    
    excerpt = exceprt_conclusion[0]
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)
        
        review.ssid = product.ssid
    
        product.reviews.append(review)        
    
    if product.reviews:
        session.emit(product)
        