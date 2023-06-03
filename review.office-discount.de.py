from agent import *
from models.products import *


OPTIONS = "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=vZCqGZcHSeORCSb8xgWkvhtOcmQAAAAAQUIPAAAAAAAUHg/Wn3j7BnFcb9s/GpyL; reese84=3:ziC/N7+7tdGlDw3s7RfmbQ==:1OvWM/GESVag7X5GcjYW5Vnt9paUG5SumwyVp4j6ZeixnPYTJ9wPWy1lIPzMcUSUIGS9Y9DArX7Z0MnWkNXOHGItsxNymIJVQPTcsaxZ5jzs8RZT1KgoFLbx2YITFxxLhZOdGYkhNdkyfgYTLiLYHszvnfI4v8X3WbOayoVrPmthGsH22/dag+2f+SNZVpHU0PYvg18yDdljmG2n9Xmhg4Qv3IrC5wgH750eywtHmZVGoXtZ99Y0tBSiNGyytN6UEbLWGDznYqSga8gjBdz3e1fPER6v3uzY6wywad3K1A/McDczkQNzrkN/HsR4zVbLtrlqqjRwJczYO2G6UD6n6ICgGoMDMlEazT78B4hAqmPdGzIHywA/ICJrCQZjZcNnv4/jSx4L/Qz2xZ55whFeVKV1uxHeo2dd+VrEdmzp9yAAVxZ2mInjUBtVQwNJIsaBJqaaJ58ckD7uoNYUMZqhdMliBf5MUxZ25yqVsz7sCnA=:lieAz2q7ap/7w0KhacQPeIN6sPHlTeTlg8wthSrcOs8=; SSLB=1; SSID=CQANyB0qAAwAAAAfTnJkcF1AAB9OcmQGAAAAAADW3lpmegR6ZADJiv0CAAOPdgAAKqp5ZAMA_AIAAyF2AAAqqnlkAwCEAgAB9lwAAHoEemQBAOoCAADtAgAA7AIAAA; SSRT=zwZ6ZAADAA; uvid=02b664cc-d53d-4eb8-b09d-88fe2e66b261; WC_PERSISTENT=Yih5AptDkfs6AresKTYDqWm2871SWdwn8jP2%2Fe1Ui5w%3D%3B2023-05-27+20%3A38%3A23.051_1685212703043-520431_10006_-1002%2C-3%2CEUR_10006; _ga_7GM3G61HNK=GS1.1.1685718134.6.1.1685718756.39.0.0; _ga=GA1.1.997405017.1685212719; _fbp=fb.1.1685212722852.1529141951; cto_bundle=Kora6F8wRkRNckVsZmc3c2FZVmlSVlo2dm9QdzA5c0hickd6Sk45cFdJQktoZlRBY1YyUmowUWVnMndnZkdCZVRmTDZFc2ZrY3VaUWNTJTJGWDBock10djZucmlrYjJDRDhaM3FVY2hOVlZxJTJGOUZuRyUyQk01N1ZwVXlQbnJpa3lYb0ZaRkpzbnlsWGVSclJ1c01sTm9yazV4NUU4c3clM0QlM0Q; mf_user=ecf28b6dd5898f3b51805c049b488d06|; incap_ses_521_2623194=gF7oMyW753AMfKFty/c6B8C0emQAAAAAC7H5P3hKmdIpzH4OLREtUg==; nlbi_2623194_2147483392=J937B0N9/15jHZZ8iGaaigAAAADICb11QcFjcZZp6OZsI3lW; WC_GENERIC_ACTIVITYDATA=[6129132644%3Atrue%3Afalse%3A0%3AIo%2BP2I%2BLdfenNDIRuobDtUT4BT22ZdW0sYdXsJxF4CU%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685212703043-520431][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; WC_ACTIVEPOINTER=-3%2C10006; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; JSESSIONID=0000XOXqk-JB0RgebH_kDm7fohi:1bj7vub5m; WC_SESSION_ESTABLISHED=true; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1498267454%2CuYYwd%2FMIUhfVR%2BzrriPc1g0WIjURoc0%2FWI%2BH3LbwqYD2Sltm0rOUmdSDfnlq4ase74WNPTyP%2FpLCv0e9GAxvEMkp8O9KPYunSFP4EBhaVEvrnZfnBgQtDZU46D0pM9u5sNK7YRws8B04xO3Bikayla8OxYZ8Tzy%2FWw7pfG3tGBXp4rgexZxYpDqkwU3X8rDgJ2tf6jlHdLiqyM8VZkaUqPvK%2FxTuR0TEcqg23c1ZtB%2FM8bs%2FSJm0d0PjKx5MSWc%2F; nlbi_2623194=7uCCAF1sMgnPDzxWiGaaigAAAAAoo11G1aBbneIg4YmwuTQJ; SSSC=22.G7237933446192979312.6|644.23798.0:764.30241.1:765.30351.1; 3a3276486f1fdb89f1eb46f1a28ff467=83bb121dcd854fbf301b13391285e969; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=|.47.1685718738465|1685695023771||0|||1|0|31.21708; _gid=GA1.2.228582243.1685695024; uslk_umm_52132_s=ewAiAHYAZQByAHMAaQBvAG4AIgA6ACIAMQAiACwAIgBkAGEAdABhACIAOgB7AH0AfQA=; 1a18f263d16cb79a11d81f44e69081f6=4fc82fdb75e0790302914fcdd0ddcd03; skz=1086274' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1'"


def run(context, session):
    # session.queue(Request('https://www.office-discount.de/papier/additions-fax-kassenrollen?mkz=0', force_charset='utf-8', use='curl', options=OPTIONS), process_category, dict(cat="test"))
    session.queue(Request('https://www.office-discount.de/', force_charset='utf-8', use='curl', options=OPTIONS), process_frontpage, dict())


def process_frontpage(data, context, session):    
    cats1 = data.xpath('//div[@class="wrapper"]//ul/li[@id]')
    for cat1 in cats1:
        name1 = cat1.xpath("a//text()").string()
        categoryid = cat1.xpath('@data-categoryid').string()
        print('categoryid=', categoryid)
        cats2 = session.do(Request('https://www.office-discount.de/ugsservices/diqson/10006/categories/'+categoryid, force_charset='utf-8', use='curl', options=OPTIONS), process_cats2, dict())
        print("cats2=", cats2)
        # https://www.office-discount.de/ugsservices/diqson/10006/categories/SHO.20187799.8
        # cats2 = data.xpath('//div[@class="wrapper"]/div[contains(@class, '+cat1_id+')]/div[@id="ajax"]/div/ul/li')
        # for cat2 in cats2:
        #     name2 = cat2.xpath('a//text()').string()
        #     url = cat2.xpath("a/@href").string()
        #     session.queue(Request(url, force_charset='utf-8', use="curl", options=OPTIONS), process_category, dict(cat=name1+'|'+name2))


def process_cats2(data, context, session):
    

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
        session.queue(Request(next_page, force_charset='utf-8', use="curl", options=OPTIONS), process_category, dict(context))
        

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']
    
    sku = data.xpath('//table[@class="keyfacts"]/tr/td[@class="jsArticleNumber"]/@content').string()
    print("sku=", sku)
    if sku:
        product.sku = sku
    
    ean = data.xpath('//meta[@itemprop="gtin13"]/@content').string()
    if ean:
        product.add_property(type='id.ean', value=ean)

    revs = data.xpath('//div[@class="rating-item"]')
    for rev in revs:
        review = Review()
        review.type = "user"
        review.url = product.url
        review.date = rev.xpath('div[@class="details"]/span[not(contains(@class, "author"))]//text()').string()
        
        author = rev.xpath(".//span[@class='author']//text()").string()
        review.authors.append(Person(name=author, ssid=author))
        
        grade_overall = rev.xpath('.//div[@class="star"]/@data-value').string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))
        
        excerpt = rev.xpath(".//p[@class='text']//text()").string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)           
            review.ssid = excerpt
            product.reviews.append(review)

    if product.reviews:
        session.emit(product)