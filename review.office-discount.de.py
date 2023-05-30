from agent import *
from models.products import *


OPTIONS = "-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Referer: https://www.office-discount.de/ordner-mappen' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=YstLhqBXR16BypODDBiKNIxDdGQAAAAAQUIPAAAAAAB1QxfwulJVKWK3j7xg8Spc; incap_ses_1572_2623194=UM53WC+Sv2SxY3ao/93QFc6bdGQAAAAAL4kEnGs9rYIAs8btWCzzVA==; nlbi_2623194=aQCKT1r9+jSP7y+kiGaaigAAAADoEYPIIBNb0K8GDdm7LaMN; nlbi_2623194_2147483392=Le2weVUTVUKz0ir4iGaaigAAAAApo84E1e2Xs9HVpdBoF8/8; reese84=3:IOOFvSxhGyypy1rsq6iquA==:CnihaIEV7A4w4cbV/hBGDRtK5+BzQZw/ucY/5+0Um0XPM0GirXnqboQ1BLyWY/DUXJNundwxy9vKeNm53SEq0i2aJuRbCCgiunvdcwfWNXDNFoz4GyTTVM+lJQyKUvHj/+u7GZFRPYzbGdNWJO4NHXun+zMWaPs6R3jCBFVfD928fK0+PZ83nh+zfBoHCnXcLUnhs06/pIhvfmtR110MBgGYxvmOo3I8QolWMEdz0WygJkwAuFoJhhroLEJsU9BNDXvVYfbwspc6ILERQ5pAG3xcfguvihwdfuNgJIIK3EFEX51h7nFLfal/rHvvpNI+CzTv8vpZg8NX3th3/dY8nAcTSxdjAeJikpyUGS8mP2SaFp4W4tYhn3WKCgRIbyClV/NBalocxqKwZ4npCGu0LZdFvJq10eLIpb3f+2BQoSYQ1pXU7rAIhG5M7MAydubCyKOUYtn2VswKIE4tO2xijtYHcr/6gEal9Pjswv296bc=:6blJXM/+f8ZQu9OMGyknxP9xFV4HaUUFopWOpSvZiCg=; SSLB=1; SSID=CQBNeh04AAAAAACOQ3RkyhhAAI5DdGQCAAAAAAA6eFVmzpt0ZADJioQCAAH2XAAAzpt0ZAEA7QIAAQ9zAADOm3RkAQDsAgAB53IAAM6bdGQBAOoCAAOtcgAAjkN0ZAIA; SSRT=zpt0ZAADAA; WC_GENERIC_ACTIVITYDATA=[6116084569%3Atrue%3Afalse%3A0%3AkpNSZ4rWE1HTCLd6%2BOOzWXcQ4uhRkuPMdFtx8hpz3AU%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685341070495-809952][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; ecToken=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJXQyIsImV4cCI6MTY4NTM2NDg2MiwianRpIjoiZEhiZEJvZlh5QnptTHJBMlBfei1GZyIsImlhdCI6MTY4NTM2MzY2Miwic3ViIjoidXNlcl9qd3QiLCJzaG9wQ3VzdG9tZXJOdW1iZXIiOiItMTAwMiIsInJlZ2lzdHJhdGlvblR5cGUiOiIiLCJzYXBDdXN0b21lck51bWJlciI6bnVsbCwic3RvcmVJZCI6IjEwMDA2IiwiYXVkIjoic2VydmljZXMifQ.oFrQVB_HYb3gAjSCqVlFGL8_FEhaICHMR9Ad9Y0RUvFeIakeH0R6c5wDXvFfBRIK8V70cExSvbvZXoaFMWs0ye4MZYyRA8Z6Jzkoqix6TiNdlp_bdaFeV6hLS4Lw76-buXdDauNADNM4oKqd8ZQSEU0eL2aEeJx6TEVo_lxBC3rqiDITCccHErwRULSwLQdYB_L_JJp_MtVztwALbByiPLUgupHU-wJe22xp-kRAF759OVnwBConYntF4bQ6kkciY-YLTPs2_xFJNaFbpYitbkog90CljwCsy1HaxNSW1DcY0wcKPrc-e_1iSiZlnW2Ld9PlzyRJ7axccMoYjBmpow; WC_PERSISTENT=MKOjGnXLUev8jdv43S9eS0%2BrqAfw%2Fx5dH48vfo58OC8%3D%3B2023-05-29+08%3A17%3A50.5_1685341070495-809952_10006_-1002%2C-3%2CEUR_10006; WC_ACTIVEPOINTER=-3%2C10006; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; uvid=493714b8-afe8-402c-8725-7c98f56a0bae; JSESSIONID=0000Vl8hSGWxNnope8sxqwTfQPO:1bj7vt3bc; WC_SESSION_ESTABLISHED=true; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1362788575%2C6GTMdu3mv98ClCGl9jOCOmMlq7FOxiErTSN%2BlrSdCdaBvbPfsfEVnNFZe4aX5iH%2BM%2B9N8aKVEeeJcFu89F3uE4K%2FlddkZlXrBg1wV%2FSE9CPlpjyU4pQysz3%2FcO6ICTxAVd%2F9759EoY4BZiWfDfagltIvcpXXfnL05gb3Y9TZBULO4lt4pa3oj5rFlARnhIpw1%2BHzAo%2B%2FK2Ex9FVWmnW4jqK8uuvpQWFQoUFZVrSl102XP0xos0UQxO0meFi3EPf7; SSSC=22.G7238484778259847370.2|644.23798.0:746.29357.1:748.29415.0:749.29455.0; _ga_7GM3G61HNK=GS1.1.1685363662.2.1.1685363666.56.0.0; _ga=GA1.1.1922368939.1685341080; _gid=GA1.2.1159212601.1685341081; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=94cee4da1593b8b9ed194f5ecfeed0f2|052955236461d2f7bf159a21efe5d0069fd3ab46.47.1685350138516$0529540703d48822232c4ba2f55b646132a72762.47.1685355840951$05291058f7332db07b02a2f67a4e66382166b066.47.1685356213622$052955941cf7c916398d826f76a16e76d793f75b.47.1685356319508$05293597d3fd00172367c14cc3d8c4e41cdc6328.47.1685356417426$0529262233f4a68f28898a960cd3cf009bc7cbb8.1037162625.1685363692487|1685363973305||1|||0|17.88|3.85882; _fbp=fb.1.1685341081721.1168505427; cto_bundle=H_DyAl9CM1pkbmlKTzdyMjRKUkVQNjk2cWFTSVN2a1EySnZHSWJBd05RcjV0NU16NWtjZFpQek5OOFlnQVBVQUc0WEhTOUVtUGtxSUc5WTcwdSUyQk90MkprbDB4YkFvTGhPNU9jQUNHNDN6M1Axb24wb0NiT25pWEFLbTl1ODM1cGZWdmxmU0l4TFZSWlZCcUxVUyUyRmJVQ1dzZHF3JTNEJTNE; mf_user=8c0d46e87e7bfce20c7f721d83975fe1|; 3a3276486f1fdb89f1eb46f1a28ff467=83bb121dcd854fbf301b13391285e969; incap_ses_1084_2623194=qAvVTtmfTUBK8rHlMyULDy+WdGQAAAAAC5OkNrzdq2iTFZaQXSszwg==; skz=27079828' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'TE: trailers'"


def run(context, session):
    session.queue(Request('https://www.office-discount.de/', force_charset='utf-8', use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):    
    cats1 = data.xpath('//div[@class="wrapper"]/nav[@class="header-nav fullscreen"]/ul/li[@id]')
    for cat1 in cats1:
        name1 = cat1.xpath("a//text()").string()
        cat1_id = cat1.xpath('@id').string()
        cats2 = data.xpath('//div[@class="wrapper"]/div[contains(@class, '+cat1_id+')]/div[@id="ajax"]/div/ul/li')
        for cat2 in cats2:
            name2 = cat2.xpath('a//text()').string()
            url = cat2.xpath("a/@href").string()
            session.queue(Request(url, force_charset='utf-8', use="curl", options=OPTIONS), process_category, dict(cat=name1+'|'+name2))


def process_category(data, context, session):
    prods = data.xpath('//div[@class="plist"]/div[contains(@class, "product plist_element jsArticleElement"]')
    for prod in prods:
        prod = prod.xpath('/div[@class="plist_content"]/div[@class="article-content"]/div[@class="plist_details"]/strong[@class="hdl"]')
        url = prod.xpath('a/@href').string()
        name = prod.xpath('a/span//text()').string()
        session.queue(Request(url, force_charset='utf-8', use="curl", options=OPTIONS), process_product, dict(context, url=url, name=name))
    
    next_page = data.xpath('//a[@data-reference="next"]/@href')
    if next_page:
        next_url = next_page[0].string()
        session.queue(Request(next_url, force_charset='utf-8', use="curl", options=OPTIONS), process_category, dict(context))
        

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    
    sku = data.xpath('//table[@class="keyfacts"]/tr/td[@class="jsArticleNumber"]/@content')
    if sku:
        sku = sku.string()
        product.sku = sku
    
    ean = data.xpath('//meta[@itemprop="gtin13"]/@content')
    if ean:
        ean = ean.string()
        product.add_property(type='id.ean', value=ean)
    
    context['product'] = product
    process_reviews(data, context, session)
    
    
def process_reviews(data, context, session):
    product = context['product']

    revs = data.xpath('//div[@class="rating-item"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('//div[@class="details"]/span[not(contains(@class, "author"))]//text()').string()
        
        author = rev.xpath(".//span[@class='author']//text()").string()
        review.authors.append(Person(name=author, ssid=author))
        
        grade_overall = rev.xpath('.//div[@class="star"]/@data-value')
        if grade_overall:
            grade_overall = grade_overall.string()
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))
        
        excerpt = rev.xpath(".//p[@class='text']//text()")
        if excerpt:
            excerpt = excerpt.string(multiple=True)
            review.add_property(type='excerpt', value=excerpt)           
            review.ssid = excerpt
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)