from agent import *
from models.products import *
import simplejson


BASE_URL = 'https://www.office-discount.de/'
OPTIONS = "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Referer: https://www.office-discount.de/lager-betrieb/lagereinrichtung?mkz=0' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=vZCqGZcHSeORCSb8xgWkvhtOcmQAAAAAQUIPAAAAAAAUHg/Wn3j7BnFcb9s/GpyL; reese84=3:bYBy2rCIsP6m7JNUT0fMGg==:lLNDiGhKQYQ17esVvssn8THLmAX5UUDq1oFM0upGIfx++UTpqA2WB3t9HNoAabpTJ901Zl+9FT2XcCwZFqyzINsab7KCiUShFIUlV8wXTHPgbfm7lL3a+JBGCUwcL9Z1sosMKfucR8IW/tMjYfFtLdfab586MjNPjGOaFDzUHi6psTbQ9d1awMUbTwe8yR/yVTPl1ZULNMkbvcEfPinlqAYlUXiXdK1ZMo3fOK6xbjJY2Z8jWhCLC2bnjgHyRI+Hc/3LRAq2CWqeTKhaOgnQGvAjvz8rRLufoeirZDVKZLhJ6Zxt4482p6jatw6zXvwZ1p2p3nWzzhR63l0I/ODrCVQPqHE+LdsQkCROmQAKLYE+CvXh1vo0GsjTRTnFmxCpjQgZyQtKmylG9CDoq/AdJDolwP/h2q+8zsp4npQa9ABw/FdNFpvbwoQwSTnYQsDC9P6I0pZlHgRYWgjWxdpKXQ==:hg4THK3YivsoJu20uop7YoiEhJ1s9ME0plfE7tgcz84=; SSLB=1; SSID=CQAaGh0qAAwAAAAfTnJkcF1AAB9OcmQJAAAAAADW3lpmG-59ZADJioQCAAH2XAAAG-59ZAEA_AIAAyF2AAAqqnlkBgD9AgADj3YAACqqeWQGAOoCAADtAgAA7AIAAA; SSRT=LfB9ZAADAA; uvid=02b664cc-d53d-4eb8-b09d-88fe2e66b261; WC_PERSISTENT=Yih5AptDkfs6AresKTYDqWm2871SWdwn8jP2%2Fe1Ui5w%3D%3B2023-05-27+20%3A38%3A23.051_1685212703043-520431_10006_-1002%2C-3%2CEUR_10006; _ga_7GM3G61HNK=GS1.1.1685974555.9.1.1685975091.55.0.0; _ga=GA1.1.997405017.1685212719; _fbp=fb.1.1685212722852.1529141951; cto_bundle=BriJYl9wcDhhJTJGa1BPN3JCcE9rTyUyQlVxdDRkTWRQN0s1V0dpdnpYT2lRUnY4VXI0NDElMkZhNDFkaHZKaVp1ZEozSXE4dTJWTEdWeEIyRFFLeXRsRGhiMFN0SzFEVzFoVzhPYWFRWU5NaDNBbFglMkJQUnIwZzAyWVVsZVZ4OCUyRmJBS05EaTBTV1hZWWdpaURBbUhDRHZlbW4zT1FqbUxnJTNEJTNE; mf_user=ecf28b6dd5898f3b51805c049b488d06|; uslk_umm_52132_s=ewAiAHYAZQByAHMAaQBvAG4AIgA6ACIAMQAiACwAIgBkAGEAdABhACIAOgB7AH0AfQA=; incap_ses_324_2623194=IcMDXu8jsGz1KBOM5BR/BK3rfWQAAAAAw85JHPaTOI2O4QNR4YcKOw==; nlbi_2623194_2147483392=kPGPEI0W3iiFQMgQiGaaigAAAAD/iICkzdlIgdtRviLJCXRP; WC_GENERIC_ACTIVITYDATA=[6135901115%3Atrue%3Afalse%3A0%3A2zIBCpJVx82iPa5W%2FnIWhF83db0cHxoKkjaKQcmW6WU%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685212703043-520431][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1646801608%2CYDHY8WwlPTKJxese8YiU4nybBOyuttF6YTqjeS2ATn%2FTHhINB7S1aBmOLVoqXBE2dyCtlIF85mClbOOJjuhyxwSzHxV4KjQ7rzz0QfJanb3TBAp%2FdgotXJN%2Byj%2BsT5G0%2BE3S3q%2FHRIlZf9nu4nPX6A8r%2FMf6yKQzf5q4xfrXZI%2Fk71xTUYDqa6iG5Z33xEBHUyl7Ysf8fCtPghWoAX2DpfaBVEl%2FzAK1LDAQr%2B6FGxM8oWIys98H7PM1w9QypEGQ; WC_SESSION_ESTABLISHED=true; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; WC_ACTIVEPOINTER=-3%2C10006; JSESSIONID=0000FGe7iiWPPcAKJeBcBdNJjRY:1bj8008j6; nlbi_2623194=OjkSQqxqYB3gsvKfiGaaigAAAAC3CHR2BpPF3PNM65PbpNjx; SSSC=22.G7237933446192979312.9|644.23798.0:764.30241.1:765.30351.1; _gid=GA1.2.361039161.1685934642; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=|.-9650919960.1685975090748|1685934642944||0|||1|0|33.44607; 3a3276486f1fdb89f1eb46f1a28ff467=03cda7e8b0f796a0cbcbc6d4cfc4c532; 1a18f263d16cb79a11d81f44e69081f6=0839a54f5200e3ffe4da5fb5a1f42356; ss_eaaWkButton=ALL; ecToken=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJXQyIsImV4cCI6MTY4NTk3NjI4NSwianRpIjoiajhwbzhsZ0ZwUG9rcldlYUlnMV94USIsImlhdCI6MTY4NTk3NTA4NSwic3ViIjoidXNlcl9qd3QiLCJzaG9wQ3VzdG9tZXJOdW1iZXIiOiItMTAwMiIsInJlZ2lzdHJhdGlvblR5cGUiOiIiLCJzYXBDdXN0b21lck51bWJlciI6bnVsbCwic3RvcmVJZCI6IjEwMDA2IiwiYXVkIjoic2VydmljZXMifQ.X3OPCquX_15GQ25om3ENfgajZFZuKb5YGLDZlmp9KU7BZeUNhm3dvdTDiRvqzPDiUfTYg9qfiCTjppMVRkpGhYWxBvcsLVRvjCP1DxVYtMoly5Sh10gG-hQZeA5YwGNEMvM0iZ40R7CzPPOXktppMSm5V9Tw_cF7nvVE0PPuEXX8vfU6SUsIBbvQIW2j70LUJxF0PFENqHY-1DTWYVo_ejNhireqe-mptzvmxMtYuPw7rSsf5Zm8c1fO7DdnQdESAtD9Fu09-SkeqKuvIrN0HhKwsLF3oBnd7fn8M4ruJKVjKhf-Q5eYWVwJbK_upzmcgg7n4P_U_xRjWCZbDmcstw; skz=27079822' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'TE: trailers'"
# curl 'https://api.usercentrics.eu/settings/Jur1xYv8X/latest/de.json' -X OPTIONS -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Access-Control-Request-Method: GET' -H 'Access-Control-Request-Headers: content-type' -H 'Origin: https://www.office-discount.de' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site'

def run(context, session):
    # session.queue(Request('https://www.office-discount.de/25-vp-flaschenbeutel-rot-9-5-x-38-0-cm-589671', use='curl', options=OPTIONS), process_product, dict(cat="test", url=BASE_URL, name="test_name"))
    session.queue(Request(BASE_URL, use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):    
    cats = data.xpath('//div[@class="wrapper"]//ul/li[@id]')
    if not cats:
        print('no_data=', data.raw)
    print('cats=', cats.pretty())
    for cat in cats:
        name = cat.xpath("a//text()").string()
        categoryid = cat.xpath('@data-categoryid').string()
        print('categoryid=', categoryid)
        session.do(Request(BASE_URL+'ugsservices/diqson/10006/categories/'+categoryid, use='curl', options=OPTIONS), process_subcatogory, dict(cat=name))
        # https://www.office-discount.de/ugsservices/diqson/10006/categories/SHO.20187799.8
        # cats2 = data.xpath('//div[@class="wrapper"]/div[contains(@class, '+cat1_id+')]/div[@id="ajax"]/div/ul/li')
        # for cat2 in cats2:
        #     name2 = cat2.xpath('a//text()').string()
        #     url = cat2.xpath("a/@href").string()
        #     session.queue(Request(url, use="curl", options=OPTIONS), process_category, dict(cat=name1+'|'+name2))


def process_subcatogory(data, context, session):
    sub_cats = simplejson.loads(data.raw)['detail']['hierarchy']['children']
    # print("data_cats2=", cats2)
    for sub_cat in sub_cats:
        url = BASE_URL + sub_cat['seoUrl']
        print("url_cat2=", url)
        name = sub_cat['name']
        print('name_cat2=', name)
        session.queue(Request(url, use='curl', options=OPTIONS), process_category, dict(cat=context['cat']+'|'+name))
    
    
def process_category(data, context, session):
    prods = data.xpath('//div[contains(@class, "product plist_element jsArticleElement")]/div[@class="plist_content"]//strong[@class="hdl"]')
    for prod in prods:
        url = prod.xpath('a/@href').string()
        name = prod.xpath('a/span//text()').string()
        print("name_product=", name)
        session.queue(Request(url, force_charset='utf-8', use="curl", options=OPTIONS), process_product, dict(context, url=url, name=name))
    
    next_page = data.xpath('//a[@data-reference="next"]/@href').string()
    print("next_page=", next_page)
    if next_page:
        session.queue(Request(next_page, use="curl", options=OPTIONS), process_category, dict(context))
        

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    
    print('data_product=', data.raw)
    
    sku = data.xpath('//td[@class="jsArticleNumber"]/@content').string()
    print("sku=", sku)
    if sku:
        product.sku = sku
    
    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    print('ean=', ean)
    if ean:
        product.add_property(type='id.ean', value=ean)
        
    product_id = data.xpath('//div/@data-famnumber').string()
    print('product_id=', product_id)
    session.do(Request('https://www.office-discount.de/produktbewertung/index.php/api/rating/container/od/'+product_id+'/'+sku, use="curl", options=OPTIONS), process_reviews, dict(context, product=product))
    
    
def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[contains(@class, "rating-item")]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('div[@class="details"]/span[not(contains(@class, "author"))]//text()').string()
        print("date=", review.date)
        
        author = rev.xpath(".//span[@class='author']//text()").string()
        print('author=', author)
        review.authors.append(Person(name=author, ssid=author))
        
        grade_overall = rev.xpath('div[@class="stars"]/span[@class="star"]/@data-value').string()
        print('grade_overall=', grade_overall)
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))
        
        excerpt = rev.xpath(".//p[@class='text']//text()").string(multiple=True)
        print('excerpt=', excerpt)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)           
            review.ssid = excerpt
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)