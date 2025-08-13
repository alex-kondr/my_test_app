from agent import *
from models.products import *
import simplejson


OPTIONS = """--compressed -H 'Accept-Encoding: deflate' -H 'Authorization: Bearer eyJ2ZXIiOiIxLjAiLCJqa3UiOiJzbGFzL3Byb2QvYmpnel9wcmQiLCJraWQiOiJmNGU5ZDY4Ni05ZTQ1LTQ3ODQtYjFkNS00MmE2OGI0ZTFkMjciLCJ0eXAiOiJqd3QiLCJjbHYiOiJKMi4zLjQiLCJhbGciOiJFUzI1NiJ9.eyJhdXQiOiJHVUlEIiwic2NwIjoic2ZjYy5zaG9wcGVyLW15YWNjb3VudC5iYXNrZXRzIHNmY2Muc2hvcHBlci1kaXNjb3Zlcnktc2VhcmNoIHNmY2Muc2hvcHBlci1teWFjY291bnQuYWRkcmVzc2VzIHNmY2Muc2hvcHBlci1wcm9kdWN0cyBzZmNjLnNob3BwZXItbXlhY2NvdW50LnJ3IHNmY2Muc2hvcHBlci1teWFjY291bnQucGF5bWVudGluc3RydW1lbnRzIHNmY2Muc2hvcHBlci1jdXN0b21lcnMubG9naW4gc2ZjYy5zaG9wcGVyLWNvbnRleHQucncgc2ZjYy5zaG9wcGVyLW15YWNjb3VudC5vcmRlcnMgc2ZjYy5zaG9wcGVyLWJhc2tldHMtb3JkZXJzIHNmY2Muc2hvcHBlci1jdXN0b21lcnMucmVnaXN0ZXIgc2ZjYy5zaG9wcGVyLW15YWNjb3VudC5hZGRyZXNzZXMucncgc2ZjYy5zaG9wcGVyLW15YWNjb3VudC5wcm9kdWN0bGlzdHMucncgc2ZjYy5zaG9wcGVyLXByb2R1Y3RsaXN0cyBzZmNjLnNob3BwZXItcHJvbW90aW9ucyBzZmNjLnNlc3Npb25fYnJpZGdlIHNmY2Muc2hvcHBlci1iYXNrZXRzLW9yZGVycy5ydyBzZmNjLnNob3BwZXItZ2lmdC1jZXJ0aWZpY2F0ZXMgc2ZjYy5zaG9wcGVyLW15YWNjb3VudC5wYXltZW50aW5zdHJ1bWVudHMucncgc2ZjYy5zaG9wcGVyLXByb2R1Y3Qtc2VhcmNoIHNmY2MudHNfZXh0X29uX2JlaGFsZl9vZiBzZmNjLnNob3BwZXItbXlhY2NvdW50LnByb2R1Y3RsaXN0cyBzZmNjLnNob3BwZXItY2F0ZWdvcmllcyBzZmNjLnNob3BwZXItbXlhY2NvdW50Iiwic3ViIjoiY2Mtc2xhczo6Ympnel9wcmQ6OnNjaWQ6YjFlYTRkNWQtMGU5OS00YTU0LWE5YWYtYzE2OTVhMjAwYTcyOjp1c2lkOjQ2YzU2NTFkLTk5NDQtNGM2Ny1hYzQ3LTI5OGM3OWVhNmUyMiIsImN0eCI6InNsYXMiLCJpc3MiOiJzbGFzL3Byb2QvYmpnel9wcmQiLCJpc3QiOjEsImRudCI6IjAiLCJhdWQiOiJjb21tZXJjZWNsb3VkL3Byb2QvYmpnel9wcmQiLCJuYmYiOjE3NTUwNzQ0NDYsInN0eSI6IlVzZXIiLCJpc2IiOiJ1aWRvOnNsYXM6OnVwbjpHdWVzdDo6dWlkbjpHdWVzdCBVc2VyOjpnY2lkOmFibGJ4SGxyd1prdW9SbXJJWWxhWVl3WHcxOjpjaGlkOmhhc2Jyb3VzIiwiZXhwIjoxNzU1MDc2Mjc2LCJpYXQiOjE3NTUwNzQ0NzYsImp0aSI6IkMyQy0zNjk4NTQyMDE5MTQ5Njk2NjUzMzc0OTA3NzQxMTY4OTA3NCJ9.Dg4ofzTLFhizgMWVhK7_iG07LUkcqbEcWcWCYq2mcVwVdSujTcQRaxP-AmJy9T3D5lAl_PE3x__ZnxISG_jOXQ'"""



def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.hasbropulse.com/collections/shop-all-products', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[contains(@class, "chakra-stack") and .//p[contains(text(), "Brand")]]/div/div[@class="chakra-collapse"]//span[contains(@class, "chakra-checkbox__label")]')
    for cat in cats:
        name = cat.xpath('text()').string()
        prod_cnt = int(cat.xpath('span/text()').string().strip('( )'))
        url = 'https://www.hasbropulse.com/mobify/proxy/api/search/shopper-search/v1/organizations/f_ecom_bjgz_prd/product-search?siteId=hasbrous&refine=brand%3D{}&refine=cgid%3Dshop-all-products&limit=200'.format(name.replace(' ', '+'))

        if prod_cnt > 0:
            session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS), process_prodlist, dict(cat=name, prod_cnt=prod_cnt))


def process_prodlist(data, context, session):
    prods = simplejson.loads(data.content).get('hits', [])
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_product, dict(context, name=name, url=url))

    offset = context.get('offset', 0) + 200
    if offset < context['prod_cnt']:
        next_url = 'https://www.hasbropulse.com/mobify/proxy/api/search/shopper-search/v1/organizations/f_ecom_bjgz_prd/product-search?siteId=hasbrous&refine=brand%3D{cat}&refine=cgid%3Dshop-all-products&offset={offset}&limit=200'.format(cat=context['cat'].replace(' ', '+'), offset=offset)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS), process_prodlist, dict(context, offset=offset))


def process_product(data, context, session):
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

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('/text()').string()
    author_url = data.xpath('/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
