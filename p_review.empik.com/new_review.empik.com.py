from agent import *
from models.products import *


XCAT = ["Książki", "Ebooki i audiobooki", "Delikatesy", "Empikfoto.pl", "Empikbilety.pl", "PODCASTY", "PROMOCJE", "TOP"]


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    options = """--compressed -X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0' -H 'Accept: */*' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br' -H 'Referer: https://www.empik.com/dewajtis-rodziewiczowna-maria,p1394721582,ksiazka-p?mpShopId=0' -H 'content-type: application/json' -H 'Origin: https://www.empik.com' -H 'Alt-Used: www.empik.com' -H 'Connection: keep-alive' -H 'Cookie: __cfruid=a416074ca7a310e75590bacf030c8d1c840ae9ac-1697533177; portal_sticky=portal-2; CSRF=da733b23-7c5c-49b6-8b02-627174c27a5b; search-ac-popularity-gcp=disabled; season=disabled; SHOPPING_CART=e0b7ef1a-2353-4638-bc18-e7390ca5a8e3; isUsingAdbl=1; tabSetAB=search-ac-popularity-gcp:disabled:|||season:enabled:1698710400000; cf_clearance=7kgevsWFY_1y0FWnIU8oAyP2uPfvT2A86_NYOF9K1ZU-1697537057-0-1-7b81b219.7f1ee679.1d882238-0.2.1697537057; cc=1.2.3.4; cp=.1.5.19.16.30.17.34.12.10.37.3.4.35.25.26.28.27.11.29.9.8.33.21.; cva=W2.0; cvc=T; cad=1697533189467; kot_hash=bdc4efc0-cbb2-4c3d-ba18-99ba0fa8b140; ab14=v1; reco_Hash=660bea0d-f895-4caa-afd2-1722cb3982dd; JSESSIONID=AA2FBF9EFF7FBFC7D604B4E498455743.portal-2-1; RefererPromotion=EMPTY; reco_prod_id=p1394721582; reco_temp_prod_id=p1394721582' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers' --data-raw '{"operationName":"getProductStaticInfo","variables":{"id":"p1394721582"},"query":"query getProductStaticInfo($id: String!) {\n  getProduct(id: $id) {\n    id\n    baseInformation {\n      name\n      selfUrl\n      redirectUrl\n      cover {\n        id: small\n        small\n        medium\n        large\n        __typename\n      }\n      smartAuthor {\n        id: name\n        name\n        link\n        __typename\n      }\n      rating {\n        score\n        count\n        __typename\n      }\n      currentVariant {\n        label\n        prefixName\n        name\n        displayInfo {\n          icon\n          type\n          __typename\n        }\n        currentSubVariant {\n          label\n          prefixName\n          name\n          displayInfo {\n            icon\n            type\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      subtype\n      categoryInfo {\n        uxFriendlyName\n        categories {\n          id\n          name\n          url\n          __typename\n        }\n        __typename\n      }\n      promotionSoldOut\n      parentalAdvisory\n      type\n      eproductType\n      __typename\n    }\n    badges {\n      name\n      type\n      __typename\n    }\n    gallery {\n      images {\n        small\n        medium\n        large\n        __typename\n      }\n      image360 {\n        script\n        __typename\n      }\n      __typename\n    }\n    detailsInformation {\n      digitalFormat\n      datesOfSale {\n        preSaleDate\n        reSaleDate\n        __typename\n      }\n      storeAvailability {\n        isAvailableInAnyStore\n        __typename\n      }\n      freeSample {\n        url\n        format\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n"}'"""
    session.queue(Request('https://www.empik.com/gateway/api/graphql/products', use='curl', options=options), process_frontpage, dict())
    # session.queue(Request("https://www.empik.com/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    print('data=', data.raw)
    cats1 = data.xpath("//div[@class='empikNav__menu-desktop']/div/ul/li[@class='nav-categories__separator']/following-sibling::li[not(@class='nav-categories__separator')]")
    for cat1 in cats1:
        cat1_name = cat1.xpath("a/@title").string()
        if cat1_name in XCAT:
            continue
        cats2 = cat1.xpath("div/div/ul/li/ul")
        for cat2 in cats2:
            cat2_name = cat2.xpath("li/a[contains(@class, 'nav-subcategories__link--header')]//text()").string()
            if not cat2_name:
                cat2_name = cat2.xpath("li/span[contains(@class, 'nav-subcategories__label--header')]//text()").string()
            url = cat2.xpath("li[1]/a/@href").string()
            if cat2_name in XCAT:
                continue
            cats3 = cat2.xpath("li/a[not(contains(@class, 'nav-subcategories__link--header'))][not(span[@style])]")
            if not cats3 and url:
                url += "?priceTo=&rateScore=5&rateScore=4&rateScore=3&rateScore=2&rateScore=1&resultsPP=60"
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name))
            for cat3 in cats3:
                cat3_name = cat3.xpath(".//text()").string()
                url = cat3.xpath("@href").string() + "?priceTo=&rateScore=5&rateScore=4&rateScore=3&rateScore=2&rateScore=1&resultsPP=60"
                session.queue(Request(url), process_prodlist, dict(cat=cat1_name+'|'+cat2_name+'|'+cat3_name))


def process_prodlist(data, context, session):
    prods = data.xpath("//div[contains(@class, 'ta-product-tile')]")
    for prod in prods:
        name = prod.xpath(".//a[img]/@title").string()
        url = prod.xpath(".//a[img]/@href").string()
        ssid = prod.xpath("@data-product-id").string()
        session.queue(Request(url), process_product, dict(context, name=name, url=url, ssid=ssid))

    next_page = data.xpath("//link[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page), process_prodlist, dict(context))


def process_product(data, context, session):
    product = context.get("product", Product())
    if not product.name:
        product.name = context["name"].split('-')[0]
        product.url = context["url"]
        product.ssid = context["ssid"]
        product.sku = data.xpath("//tr[contains(@class, 'ta-attribute-row')]/td[contains(text(), 'Indeks:')]/following-sibling::td//text()").string(multiple=True)
        product.category = context["cat"]

        product.manufacturer = data.xpath("//a[@itemprop='author']/text()").string()
        if not product.manufacturer:
            product.manufacturer = data.xpath("//span[contains(@class, 'pDAuthorList')]/a/text()").string()
        if not product.manufacturer:
            product.manufacturer = context["name"].split('-')[-1]

    revs = data.xpath("//div[contains(@class, 'js-reviews-item')]")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.ssid = rev.xpath(".//div/@data-review").string()
        review.date = rev.xpath(".//strong[@class='nick']/preceding-sibling::text()").string(multiple=True).split(" o ")[0]
        review.url = product.url

        grade_overall = len(rev.xpath(".//i[@class='fa fa-fw fa-star active']"))
        if grade_overall:
            review.grades.append(Grade(type="overall", value=grade_overall, best=5))

        author_name = rev.xpath(".//strong[@class='nick']/text()").string()
        if author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

        excerpt = rev.xpath("div[@class='productComments__itemDescription']/text()").string()
        if excerpt:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

    if revs:
        page = context.get("page", 0) + 1
        url = product.url + "/recenzje?page=" + str(page)
        session.do(Request(url), process_product, dict(product=product, page=page))

    elif product.reviews:
        session.emit(product)
