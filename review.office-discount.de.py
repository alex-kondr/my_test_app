from agent import *
from models.products import *
import simplejson


BASE_URL = 'https://www.office-discount.de/'
OPTIONS = "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Referer: https://www.office-discount.de/haushalt-catering/gesundheit?mkz=0' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=vZCqGZcHSeORCSb8xgWkvhtOcmQAAAAAQUIPAAAAAAAUHg/Wn3j7BnFcb9s/GpyL; reese84=3:9pXtMwsyf5pMQqBEGLdgow==:475hIC1MorRgyUcIP9uhmr0uPiu8VoWUstvGqJ92d12FlydvqU5HW9XvP/IJZFUllrPl9DZjLLtW54mQyDQbtcIk8WTK3ahhWQoc3OK7kb4b5PrC0x+Kf6fv3X+pgmec+ZH3zw9qjub/+kDKoA9H9I4jcT9HvRsA2D6lm1Fuz8B05OhywrY8hAU61TulliDiEhrx3rxXcpVV87Fp9tmq8I6z4OZsyOT+zZ0zUP2GdwRkaVN8gqy5vkVClZR6xbR8hPcRDtkXF/m57YkJeiI0fUGBa1hus/tyPwBzoIS7J+IMTgZCAmSpkHMTCVchAG57QfuEYKbeWGhEBShQY7TdildUaRql7Dn/c9RgFvXfpRA4BySeAk+1d8YTfcBzef0pZAGsk251IQRT1w9EXr25/vEBMcv11n05qqPcHHbWm80I2SPmcRLZg1rlGCzn3WqO0Geu2O2TWZT/XuIkJLq1yADUlgs+Fz9uuXtk5rZmfzo=:SIMw26hQsLjDQ3s2twwa52B4TIyJE/qyeTGE1infQfA=; SSLB=1; SSID=CQAbYR0qAAwAAAAfTnJkcF1AAB9OcmQIAAAAAADW3lpmJVJ9ZADJioQCAAH2XAAAJVJ9ZAEA_AIAAyF2AAAqqnlkBQD9AgADj3YAACqqeWQFAOoCAADtAgAA7AIAAA; SSRT=jX19ZAADAA; uvid=02b664cc-d53d-4eb8-b09d-88fe2e66b261; WC_PERSISTENT=Yih5AptDkfs6AresKTYDqWm2871SWdwn8jP2%2Fe1Ui5w%3D%3B2023-05-27+20%3A38%3A23.051_1685212703043-520431_10006_-1002%2C-3%2CEUR_10006; _ga_7GM3G61HNK=GS1.1.1685934642.8.1.1685945746.55.0.0; _ga=GA1.1.997405017.1685212719; _fbp=fb.1.1685212722852.1529141951; cto_bundle=l5ETEV9FR29UMCUyRiUyRk53c05lcUJuaUdSZ290bjhMUXU4SHg5elZtb0xUdmZ3ajUlMkJGSzlQQmlYUlpRTG83Q3c5NiUyRmN1RVNxJTJGR3ZtSHJqVnpyQ2tRVkdST0FXJTJCJTJGcFJQZUhHZVdGRVpsYVhxY01hOGVTdnhtTWIxc1VCdEU5WWNBbjNCNnRRSk54YjRMUW5Hcjh5eWdMJTJGbyUyRmtqJTJCUSUzRCUzRA; mf_user=ecf28b6dd5898f3b51805c049b488d06|; uslk_umm_52132_s=ewAiAHYAZQByAHMAaQBvAG4AIgA6ACIAMQAiACwAIgBkAGEAdABhACIAOgB7AH0AfQA=; incap_ses_324_2623194=J/7OJW8k1BPz0NyL5BR/BC5lfWQAAAAAUNvzXRxdSY/1sknknK3YDQ==; nlbi_2623194_2147483392=diuMObBHh2MtO7P3iGaaigAAAABOyJC5vpECjAY40WmFocpT; ss_eaaWkButton=ALL; WC_GENERIC_ACTIVITYDATA=[6135901115%3Atrue%3Afalse%3A0%3A2zIBCpJVx82iPa5W%2FnIWhF83db0cHxoKkjaKQcmW6WU%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685212703043-520431][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; ecToken=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJXQyIsImV4cCI6MTY4NTk0Njk0MSwianRpIjoiZWVnTWxmZlljeEQzdms1SW5hSi1OUSIsImlhdCI6MTY4NTk0NTc0MSwic3ViIjoidXNlcl9qd3QiLCJzaG9wQ3VzdG9tZXJOdW1iZXIiOiItMTAwMiIsInJlZ2lzdHJhdGlvblR5cGUiOiIiLCJzYXBDdXN0b21lck51bWJlciI6bnVsbCwic3RvcmVJZCI6IjEwMDA2IiwiYXVkIjoic2VydmljZXMifQ.am3zWwn0mc-gLE8-F298GwkagFwlL7bsOHlurU4SvoDGaOODz4xUFSdM-m9yEY9iwn-qsKAPoqICgNc-U0yOpNtog3ICR3eZ5td3jTqgOA3FuXrKOfnKkxL5oKcwg1Eooe4WxIqOk2wUptgpjSAlRLDZpWzAJxiXjd0ISDIQlt1-lzxV8Ni5GP-_wY7T0SVS_ptAzVXNPZFJKQ5seTcvwcZv_Ewo5drOHbI_QPGhJGNY8xxIfupYwmWamj9iCnj4IOC9D2W29GW54r5vAwzDOia09TW1JsdVyBaebiBk2AArzyS25ty8rBWtHZQQNXvlrPBR-6rXfgat8sE4kwEgGw; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1646801608%2CYDHY8WwlPTKJxese8YiU4nybBOyuttF6YTqjeS2ATn%2FTHhINB7S1aBmOLVoqXBE2dyCtlIF85mClbOOJjuhyxwSzHxV4KjQ7rzz0QfJanb3TBAp%2FdgotXJN%2Byj%2BsT5G0%2BE3S3q%2FHRIlZf9nu4nPX6A8r%2FMf6yKQzf5q4xfrXZI%2Fk71xTUYDqa6iG5Z33xEBHUyl7Ysf8fCtPghWoAX2DpfaBVEl%2FzAK1LDAQr%2B6FGxM8oWIys98H7PM1w9QypEGQ; WC_SESSION_ESTABLISHED=true; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; WC_ACTIVEPOINTER=-3%2C10006; JSESSIONID=0000qEvmfqKYE41iAFcEU58w-og:1bj8008j6; nlbi_2623194=OjkSQqxqYB3gsvKfiGaaigAAAAC3CHR2BpPF3PNM65PbpNjx; SSSC=22.G7237933446192979312.8|644.23798.0:764.30241.1:765.30351.1; _gid=GA1.2.361039161.1685934642; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=|.-6268385304.1685945745655|1685934642944||0|||1|0|33.44607; 3a3276486f1fdb89f1eb46f1a28ff467=03cda7e8b0f796a0cbcbc6d4cfc4c532; 1a18f263d16cb79a11d81f44e69081f6=0839a54f5200e3ffe4da5fb5a1f42356; skz=27079821' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'TE: trailers'"
# curl 'https://www.office-discount.de/produktbewertung/index.php/api/rating/container/od/PRO.24267/589671' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=vZCqGZcHSeORCSb8xgWkvhtOcmQAAAAAQUIPAAAAAAAUHg/Wn3j7BnFcb9s/GpyL; reese84=3:gW29dmmStRUUQvbHIpuPfg==:9IyA0ASSIPDTS+6dwXsRVfifmBsC1pSpA+Jdxa8u4mZkFl1jCUmA5aLuXsQ7sFSLLDj+ZZQVvbbo9nVa2IU+PdGzqLfK2kTnhB0JnGwbjK1TbJoOGyz1Ja7ZTEG0Iygh8znRP5nftXcnlwmEpfXW1drajsYIUC8iGHBf3fnUY4FaOOkEnRk/FEEwrB5pN/Z0AMn56VNsIliqgUK+etGESJKIv8u7mkco2wWh2gaaD/Gy2MgjJ+mSZ8HIh/h2Gk6CmOpdTgfYnGkaAjSPD6JdZ/maVdfoyhJ8n8cOBMW53Iipu6cBi0760dxJ+9vifhw3eAmTMWgLwUBYIY18YDZZpPTDWIlsXofwqlYev2kq5INlGQeiLn3sblndOFm/mnnD3hMj+4/4KPO0CgH6hcGFEEungmlHaqorKULCenw7YxhRopJIs4OFTnAzCc3FxiKgH3SccJRsiHoPh9gUYTdnlQ==:3z20wzkiSkLYMoxcduFhoFwEfmly+c9fRhqtwCAl7mo=; SSLB=1; SSID=CQAbYR0qAAwAAAAfTnJkcF1AAB9OcmQIAAAAAADW3lpmJVJ9ZADJioQCAAH2XAAAJVJ9ZAEA_AIAAyF2AAAqqnlkBQD9AgADj3YAACqqeWQFAOoCAADtAgAA7AIAAA; SSRT=SnB9ZAADAA; uvid=02b664cc-d53d-4eb8-b09d-88fe2e66b261; WC_PERSISTENT=Yih5AptDkfs6AresKTYDqWm2871SWdwn8jP2%2Fe1Ui5w%3D%3B2023-05-27+20%3A38%3A23.051_1685212703043-520431_10006_-1002%2C-3%2CEUR_10006; _ga_7GM3G61HNK=GS1.1.1685934642.8.1.1685942346.60.0.0; _ga=GA1.1.997405017.1685212719; _fbp=fb.1.1685212722852.1529141951; cto_bundle=mRNAVF91NkRhTWQ1SXJTWUhvOUZ2emRGYmMlMkJlbW1leEx6JTJGanBlTVdkTzN6M3RkWlN4azRFNnp2SjRJbHQlMkJsZjhDRjR3MkQ1aDklMkJuYWpEbkRhcUQ2SU9OOHFCd1VOQTlqQUtOdmpFMlhkOWwlMkJRdjNBTmd6VHNOWkViM0JFanBnRWxPTHFNYWo3TDUlMkYwTFB5ZzlHSU9UWXRIR0ElM0QlM0Q; mf_user=ecf28b6dd5898f3b51805c049b488d06|; uslk_umm_52132_s=ewAiAHYAZQByAHMAaQBvAG4AIgA6ACIAMQAiACwAIgBkAGEAdABhACIAOgB7AH0AfQA=; incap_ses_324_2623194=J/7OJW8k1BPz0NyL5BR/BC5lfWQAAAAAUNvzXRxdSY/1sknknK3YDQ==; nlbi_2623194_2147483392=lOrVEQOUqGq2L4K5iGaaigAAAAC0QLTmtUaveHN2oDIyeijV; ss_eaaWkButton=ALL; WC_GENERIC_ACTIVITYDATA=[6135901115%3Atrue%3Afalse%3A0%3A2zIBCpJVx82iPa5W%2FnIWhF83db0cHxoKkjaKQcmW6WU%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685212703043-520431][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; ecToken=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJXQyIsImV4cCI6MTY4NTk0MzU0NiwianRpIjoiaHdEVTlUUk5QR1ZTa0JIQVN1MEZiUSIsImlhdCI6MTY4NTk0MjM0Niwic3ViIjoidXNlcl9qd3QiLCJzaG9wQ3VzdG9tZXJOdW1iZXIiOiItMTAwMiIsInJlZ2lzdHJhdGlvblR5cGUiOiIiLCJzYXBDdXN0b21lck51bWJlciI6bnVsbCwic3RvcmVJZCI6IjEwMDA2IiwiYXVkIjoic2VydmljZXMifQ.nJIYped8qrD1ZP19E0Ec6awnu4vNdIydkicXV6fWw2ftWSTUijsC55NSMlM7bwLR_1AuA6PbMkrWDrZDZAIHp4-XbYqanu5ZILsyDcqeMxcE3SDKx451hceQEpZte8ZgNAyLlPwRTdHuNDUyw5jDKE7GpPN-2srDoTDf2zskO3tr5Uxchix6GzpLm9P7ICXmJK0Hw2gHbT4yw_pBsuOD7XzZZN6U0OE863Hr2CptH8dXlFeDmMLBCFy-ccbv9lkjBDMREQk6oTG9er1iUUEnXzBuk1f3KswQpEvMEgSiVwhJRKBO-W_tAReEM10MCjm5qvAlPTw48i2hS2ogxCrVHw; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1646801608%2CYDHY8WwlPTKJxese8YiU4nybBOyuttF6YTqjeS2ATn%2FTHhINB7S1aBmOLVoqXBE2dyCtlIF85mClbOOJjuhyxwSzHxV4KjQ7rzz0QfJanb3TBAp%2FdgotXJN%2Byj%2BsT5G0%2BE3S3q%2FHRIlZf9nu4nPX6A8r%2FMf6yKQzf5q4xfrXZI%2Fk71xTUYDqa6iG5Z33xEBHUyl7Ysf8fCtPghWoAX2DpfaBVEl%2FzAK1LDAQr%2B6FGxM8oWIys98H7PM1w9QypEGQ; WC_SESSION_ESTABLISHED=true; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; WC_ACTIVEPOINTER=-3%2C10006; JSESSIONID=0000qEvmfqKYE41iAFcEU58w-og:1bj8008j6; nlbi_2623194=OjkSQqxqYB3gsvKfiGaaigAAAAC3CHR2BpPF3PNM65PbpNjx; SSSC=22.G7237933446192979312.8|644.23798.0:764.30241.1:765.30351.1; _gid=GA1.2.361039161.1685934642; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=|.2675582295.1685941564728|1685934642944||0|||1|0|33.44607; 3a3276486f1fdb89f1eb46f1a28ff467=03cda7e8b0f796a0cbcbc6d4cfc4c532; skz=27079817' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'TE: trailers'

def run(context, session):
    # session.queue(Request('https://www.office-discount.de/25-vp-flaschenbeutel-rot-9-5-x-38-0-cm-589671', use='curl', options=OPTIONS), process_product, dict(cat="test", url=BASE_URL, name="test_name"))
    session.queue(Request(BASE_URL, use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):    
    cats = data.xpath('//div[@class="wrapper"]//ul/li[@id]')
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
        # print("url_cat2=", url)
        name = sub_cat['name']
        # print('name_cat2=', name)
        session.queue(Request(url, use='curl', options=OPTIONS), process_category, dict(cat=context['cat']+'|'+name))
    
    
def process_category(data, context, session):
    prods = data.xpath('//div[contains(@class, "product plist_element jsArticleElement")]/div[@class="plist_content"]//strong[@class="hdl"]')
    for prod in prods:
        url = prod.xpath('a/@href').string()
        name = prod.xpath('a/span//text()').string()
        # print("name_product=", name)
        session.queue(Request(url, force_charset='utf-8', use="curl", options=OPTIONS), process_product, dict(context, url=url, name=name))
    
    next_page = data.xpath('//a[@data-reference="next"]/@href').string()
    # print("next_page=", next_page)
    if next_page:
        session.queue(Request(next_page, use="curl", options=OPTIONS), process_category, dict(context))
        

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    
    # print('data_product=', data.raw)
    
    sku = data.xpath('//td[@class="jsArticleNumber"]/@content').string()
    print("sku=", sku)
    if sku:
        product.sku = sku
    
    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    # print('ean=', ean)
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
        # print("date=", review.date)
        
        author = rev.xpath(".//span[@class='author']//text()").string()
        # print('author=', author)
        review.authors.append(Person(name=author, ssid=author))
        
        grade_overall = rev.xpath('div[@class="stars"]/span[@class="star"]/@data-value').string()
        # print('grade_overall=', grade_overall)
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))
        
        excerpt = rev.xpath(".//p[@class='text']//text()").string(multiple=True)
        # print('excerpt=', excerpt)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)           
            review.ssid = excerpt
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)