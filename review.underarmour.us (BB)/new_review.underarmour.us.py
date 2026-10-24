#!/usr/bin/python
# -*- coding: utf-8 -*-
from agent import *
from models.products import *
from lib.bazaarvoice_api_reviews import *


XCAT = ["New & Featured", "Curry", "Back to School", "Outlet", "Shoes"]


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


# def Request(url):
#     options = """--compressed \
#     -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
#     -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
#     -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' \
#     -H 'Accept-Encoding: deflate' \
#     -H 'Referer: https://www.underarmour.com/en-us/' \
#     -H 'Connection: keep-alive' \
#     -H 'Cookie: consentBannerAcknowledged=true; ua-bot-class=none; ua-bot-name=; _fs_cd_cp_pRdRgnTnF68pCV2F=AScx4_4XUciH-N-pRnu0Ou1xT7VqAGt_0X-RF_TUb-sZ5n-bnvCdQMBUNz_TGzbO3DqDQ4Lcc3O5cgXrZ3LmL8da5rgwQ6R3CTJvxykh9M9LxV8D2EL5DzDxI30ZodbxcyFi_dXXVZmUa1y8-mQn2vVWhGGnX1uWa-AzyWH98greqPUFCDb1egxeWgn-Dyt56hvBgbDajA==; _fs_ch_cp_79UUvfpJ5mWYtLQv=AYBCVKnW1VQXcgx30Rz-2bJdyXQiMFsARbmbe947SmHFXAA-N9-XrvMA9J6z3cihHMdHtbpsJ2s1P-fhNxboJbTOhsYe5uo3qBeh2a7NV6pKqTCj77uT_PwISWaHcdoBBmzMdJTk0CMm5HnhSyh7yG9PkurzlAFfbnX9DtiUqcPnB_8PIPlYvZnaTPXJUvzy3XEy9nMyb-AviKIQwGHe2pBOJ_0ih4oTKqQR6Lsj8MhvbYHna7HxIG0X-rQes40E7R5rivsZMWbgBitQZbsStFoq3N8Zt_RUtuK60Xe0VGZeleBXpQLvKA5AumwtEs8Oi-OWnD8DKGAz7hWKGAgM6hXlA7nbGBxrv8LTuZVmp2K67frNUHYGJvtvy4pUK5_d7I_z3fYBWLey8Lckju7rLJWTDQRaTLEvDIUNXUM=; newVisitorCookie=second; ConstructorioID_client_id=86f896ac-25fd-4213-b15e-1c8f1be5eb4b; ConstructorioID_session_id=1; ConstructorioID_session={"sessionId":1,"lastTime":1792817168929}; notice_preferences=2:; notice_gdpr_prefs=0,1,2::implied,eu; TAconsentID=95f6f415-995a-49b3-9f1e-28eeb220705f; cmapi_gtm_bl=; cmapi_cookie_privacy=permit 1,2,3; _dd_s=aid=c0b044ce-d9c1-41df-a4dc-d0fbe54100dd&rum=1&id=f8cfb299-dd57-4d4a-a1af-087914567009&created=1792816102479&expire=1792818772469; ConstructorioID_client_id=86f896ac-25fd-4213-b15e-1c8f1be5eb4b; notice_behavior=implied,eu' \
#     -H 'Upgrade-Insecure-Requests: 1' \
#     -H 'Sec-Fetch-Dest: document' \
#     -H 'Sec-Fetch-Mode: navigate' \
#     -H 'Sec-Fetch-Site: same-origin' \
#     -H 'Priority: u=0, i' \
#     -H 'Pragma: no-cache' \
#     -H 'Cache-Control: no-cache'"""
#     r = agent.Request(url, proxies=['rotating-us'], use='curl', force_charset='utf-8', options='-s -L --insecure '+options, max_age=0)
#     return r


def RequestProds(url, offset):
    # category = url.split('/c/')[-1].replace('mens/', 'men/').replace('womens/', 'women/').strip('/').replace('/', '-')
    # data = {
    #     "query": "query ProductGridBrowse($refinement: SearchRefinementInput, $amount: LimitQuantity, $sortDirection: String, $offset: Int, $src: String, $clientId: String, $sessionId: Int, $includeShopTheLookInfo: Boolean = false) { browse( refinement: $refinement sort: $sortDirection offset: $offset limit: $amount src: $src clientId: $clientId sessionId: $sessionId ) { ...ProductGridCommonFragment edges { node { ...ProductGridCommonMasterFragment ...ProductGridCommonSlicedFragment __typename } __typename } __typename } } fragment ProductGridCommonFragment on SearchProductConnection { sortingOptions { id label selected __typename } totalCount resultId redirectUrl pageInfo { hasNextPage endCursor __typename } refinementAttributes { label attributeId values { label selected hitCount description __typename } __typename } __typename } fragment ProductGridCommonMasterFragment on MasterProductSearchHit { __typename mcpSKU style productName subHeader orderable exclusiveType comingSoonMessage preorderable preOrderProductTileMessage url isOutletCategory outletColors giftCardType prices { list { min max __typename } sale { min max __typename } __typename } promoPrices { min max __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } badges { upperLeft bottomLeft upperLeftFlameIcon __typename } colors { team color name hideColorway hex hex secondaryHex orderable isLoyaltyExclusiveColor assets { title alt images { url assetName viewType __typename } __typename } prices { list { min max __typename } sale { min max __typename } __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } __typename } sizes { size __typename } shopTheLookInfo @include(if: $includeShopTheLookInfo) { status colors { color images { image modelHeightCm materialCodes { color __typename } modelSize __typename } __typename } __typename } } fragment ProductGridCommonSlicedFragment on SlicingGroupSearchHit { __typename mcpSKU slicedProductId productName subHeader orderable preorderable preOrderProductTileMessage url isOutletCategory outletColors colors { team color name hideColorway hex secondaryHex orderable isLoyaltyExclusiveColor assets { title alt images { url assetName viewType __typename } __typename } prices { list { min max __typename } sale { min max __typename } __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } __typename } badges { upperLeft bottomLeft upperLeftFlameIcon __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } prices { list { min max __typename } sale { min max __typename } __typename } promoPrices { min max __typename } sizes { size __typename }}",
    #     "operationName": "ProductGridBrowse",
    #     "variables": {
    #         "includeShopTheLookInfo": False,
    #         "refinement": {
    #             "hitType": ["MASTER", "SLICING"],
    #             "category": 'girls-clothing-tops',
    #             "customRefinements": [
    #                 {
    #                     "attributeId": "orderable_only",
    #                     "values": ["true"]
    #                 }
    #             ]
    #         },
    #         "amount": "TWENTY_FOUR",
    #         "sortDirection": "now-trending",
    #         "offset": offset,
    #         "src": None,
    #         "clientId": "86f896ac-25fd-4213-b15e-1c8f1be5eb4b",
    #         "sessionId": 1
    #     }
    # }
    # data = simplejson.dumps(data)
    # options = """-X POST \
    # -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' \
    # -H 'Accept: application/json, text/plain, */*' \
    # -H 'Accept-Language: en-us' \
    # -H 'Accept-Encoding: gzip, deflate, br, zstd' \
    # -H 'Referer: https://www.underarmour.com/' \
    # -H 'content-type: application/json' \
    # -H 'uaclienttype: seabiscuit/3.28.1' \
    # -H 'ua-language-code: en' \
    # -H 'ua-site-code: US' \
    # -H 'authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik1UVTVOa1UwTVRaQk5EbEdNekU0TjBKRlEwVkJRVVkzTWtFeU5EZEZNVU00T0Rjd01VTTBPUSJ9.eyJzdWIiOiJ7XCJzaXRlXCI6XCJVU1wiLFwiZ3Vlc3RcIjp0cnVlfSIsImV4cCI6MTc5MzQyMjY3OSwiaWF0IjoxNzkyODE3ODc5LCJhdWQiOiJodHRwczovL2NvbW1lcmNlLmFwaS51YS5jb20iLCJpc3MiOiJodHRwczovL2FwaS5zaG9wLnVhLmNvbS8iLCJqdGkiOiJmNWNlYzAzZmE5M2U1NTI2YmQ2ZDJmNjUxMDhlYTU5MiJ9.Q5aeQEFOLpQAmG6xY4fLIPKJse54Dq1dsOniswsDVEjhBjoZChAVughAjJ_3s3FqzlIFJR_5gh7YNCa3M1XqSlJo3ZRGjgXfYz--BohAOJu30M3nGCtfaLTy6uY59U1bZ13WUEsfxorcz7x88E7pcvLwrlGqL7P-6b97Hh5AIKgNlBu4vGj5vIfYdsvJ2o0iUXQHE36WzHC6sAsiy4WVsA0Wl2SeGy5HDYaz2gLmdszlmsucdeCnJE1bEOEeRYVEhPe3xP1PuTLzlQ-4DaM24o066dwOsm4VPBH5Z0hYmd7JY2L13QC614J8LBn5QFhYn7fc2AYYccFISAVuSYo2kA' \
    # -H 'x-ua-request-signature-key: fc43b2c8b80eb3e7859de87561f995020c9b327778dc433c724765ca64973d06cd31210a49e62398e2c56cb44159d45e039978b39afaf240b6e01835d4de5b24' \
    # -H 'x-ua-request-signature: Kkc0byxfqignihZNpCpSG6XLjkQ0hHx6wVuGB3uEVsVaJSLNLPNYj+Wo95Cwa82lwrrSLBrme4n+ba8dcZcxIMOinFsWxUwNsSpQLyrYW1y2lAgF9bcd3hJKEvVUxdWNL2yHUodwJItewdVAPxPAQ6fu5CEHZNxnhRXBP4XP6P39udqJS5uTqKBwJxVsV/I1TD7hT6GxR1Ho3OO2z1W1iI5iV6nEJ5M3MoJmNRwJB32vLZ1glpN35/d0SWffDOdYRUMNFLDu1oXwB2ZF46le/v1MQ0g8jq1t/4BbKlmH0E98w6uIKow4XpMjv1PZtYOhoKcFqYW9huM5+hQ1SpiLeg==' \
    # -H 'traceparent: 00-0000000000000000b4710a9cf91801fe-3a8ef31608d794a0-01' \
    # -H 'tracestate: dd=s:1;o:rum' \
    # -H 'Origin: https://www.underarmour.com' \
    # -H 'Connection: keep-alive' \
    # -H 'Sec-Fetch-Dest: empty' \
    # -H 'Sec-Fetch-Mode: cors' \
    # -H 'Sec-Fetch-Site: same-site' """
    # options += "--data-raw '" + data + "'"
    
    target_category = "girls-clothing-tops"
    current_offset = 0

    data = {
        "query": "query ProductGridBrowse($refinement: SearchRefinementInput, $amount: LimitQuantity, $sortDirection: String, $offset: Int, $src: String, $clientId: String, $sessionId: Int, $includeShopTheLookInfo: Boolean = false) { browse( refinement: $refinement sort: $sortDirection offset: $offset limit: $amount src: $src clientId: $clientId sessionId: $sessionId ) { ...ProductGridCommonFragment edges { node { ...ProductGridCommonMasterFragment ...ProductGridCommonSlicedFragment __typename } __typename } __typename } } fragment ProductGridCommonFragment on SearchProductConnection { sortingOptions { id label selected __typename } totalCount resultId redirectUrl pageInfo { hasNextPage endCursor __typename } refinementAttributes { label attributeId values { label selected hitCount description __typename } __typename } __typename } fragment ProductGridCommonMasterFragment on MasterProductSearchHit { __typename mcpSKU style productName subHeader orderable exclusiveType comingSoonMessage preorderable preOrderProductTileMessage url isOutletCategory outletColors giftCardType prices { list { min max __typename } sale { min max __typename } __typename } promoPrices { min max __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } badges { upperLeft bottomLeft upperLeftFlameIcon __typename } colors { team color name hideColorway hex secondaryHex orderable isLoyaltyExclusiveColor assets { title alt images { url assetName viewType __typename } __typename } prices { list { min max __typename } sale { min max __typename } __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } __typename } sizes { size __typename } shopTheLookInfo @include(if: $includeShopTheLookInfo) { status colors { color images { image modelHeightCm materialCodes { color __typename } modelSize __typename } __typename } __typename } } fragment ProductGridCommonSlicedFragment on SlicingGroupSearchHit { __typename mcpSKU slicedProductId productName subHeader orderable preorderable preOrderProductTileMessage url isOutletCategory outletColors colors { team color name hideColorway hex secondaryHex orderable isLoyaltyExclusiveColor assets { title alt images { url assetName viewType __typename } __typename } prices { list { min max __typename } sale { min max __typename } __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } __typename } badges { upperLeft bottomLeft upperLeftFlameIcon __typename } productPromotions { calloutMsg promotionalPrice promotionId tooltip __typename } prices { list { min max __typename } sale { min max __typename } __typename } promoPrices { min max __typename } sizes { size __typename }}",
        "operationName": "ProductGridBrowse",
        "variables": {
            "includeShopTheLookInfo": False,
            "refinement": {
                "hitType": ["MASTER", "SLICING"],
                "category": target_category,
                "customRefinements": [
                    {
                        "attributeId": "orderable_only",
                        "values": ["true"]
                    }
                ]
            },
            "amount": "TWENTY_FOUR",
            "sortDirection": "now-trending",
            "offset": current_offset,
            "src": None,
            "clientId": "86f896ac-25fd-4213-b15e-1c8f1be5eb4b",
            "sessionId": 2
        }
    }

    payload_json = simplejson.dumps(data)
    options = "-X POST -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:158.0) Gecko/20100101 Firefox/158.0' -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: en-us' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://www.underarmour.com/' -H 'content-type: application/json' -H 'uaclienttype: seabiscuit/3.28.1' -H 'ua-language-code: en' -H 'ua-site-code: US' -H 'authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik1UVTVOa1UwTVRaQk5EbEdNekU0TjBKRlEwVkJRVVkzTWtFeU5EZEZNVU00T0Rjd01VTTBPUSJ9.eyJzdWIiOiJ7XCJzaXRlXCI6XCJVU1wiLFwiZ3Vlc3RcIjp0cnVlfSIsImV4cCI6MTc5MzQyODIxNCwiaWF0IjoxNzkyODIzNDE0LCJhdWQiOiJodHRwczovL2NvbW1lcmNlLmFwaS51YS5jb20iLCJpc3MiOiJodHRwczovL2FwaS5zaG9wLnVhLmNvbS8iLCJqdGkiOiJmNWNlYzAzZmE5M2U1NTI2YmQ2ZDJmNjUxMDhlYTU5MiJ9.DPoLC4jaNK-KFqezBjQ81skyNLCAOCL09hEEis-0FB8T9151iMvgDYNUoJLC0NktUjnxkbyZkScC4qHWdVypv8pSF5fLA5fA6gmm39uhuT2ETs2jq1M7VYvzTWCcDUQ0czqbbcjpm2QWYTLGtfAEyETFmEkl5m_1rgvDksoYz-b966RlyL7JICLIRbrDjlcNDy0H1uTFpSsmIAcX7-MPy7FDSJHAsmNdLA21gjtIXCv4YPBuB65goSEZcHZelPscqyH6eQdnkbM4PXy6Vkxb76oVxLmDurCw82jGXurgio30xuOhgoCzZ83haWZUFm5_paD4pvF3mvT281AFQkUhGg' -H 'x-ua-request-signature-key: fc43b2c8b80eb3e7859de87561f995020c9b327778dc433c724765ca64973d06cd31210a49e62398e2c56cb44159d45e039978b39afaf240b6e01835d4de5b24' -H 'x-ua-request-signature: iwoUk8o2baTuF9jhm/LRcoa4y7NG+nwMV4ZMtgX8Ub/Z5MXE2qzJ84taGhUsY3hICmqfliT5mmFPaVyiz5MUWha/zxoDvmyPfQxLyB16heXyJkI2bOeigpL8WC34/39eZJVqxSZNRg4gy7JkKBLpfTG+oca/ljmNqj1iEOCjgIzlm2uNGcbSzIMghex6Kqz+DneG0BJQOeQxysoY1tU9u72E0z8mi0mqLsZmBAWoLM+kuvTD6r3ky393kKSFlkXvFDQ7xI96hrica2Xo2x563rOTCPYHpX5xK+FegfsYYjRAfQAwzTBdUUTnanuVNr1hdaYxu6OgRU4p0OjxVuKMDA==' -H 'traceparent: 00-0000000000000000f4f53779c5f1915a-0375d0686279df35-01' -H 'tracestate: dd=s:1;o:rum' -H 'Origin: https://www.underarmour.com' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-site' --data-raw '{payload_json}'".format(payload_json=payload_json)
    url = 'https://api.shop.underarmour.com/graphql/'
    r = agent.Request(url, proxies=['rotating-us'], use='curl', force_charset='utf-8', options='-s -L --insecure ' + options, max_age=0)
    return r


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    
    # url = 'https://www.underarmour.com/en-us/c/kids/'
    # session.queue(Request(url), process_frontpage, dict(cat='cat'))
    session.queue(RequestProds('cc', 0), process_prodlist, dict())
    # session.queue(Request('https://www.underarmour.com/en-us/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@id="menu"]/li')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        if name not in XCAT:
            cats1 = cat.xpath('div/ul/li[contains(a, "Shop by Category")]/ul/li/a | div/ul/li[regexp:test(a, "Girls|Boys")]')
            for cat1 in cats1:
                cat1_name = cat1.xpath('text()|a/text()').string()

                subcats = cat1.xpath('ul/li/a')
                if subcats:
                    for subcat in subcats:
                        subcat_name = subcat.xpath('text()').string()
                        url = subcat.xpath('@href').string()
                        
                        # print name+'|'+cat1_name+'|'+subcat_name, url
                        session.queue(RequestProds(url, 0), process_prodlist, dict(cat=name+'|'+cat1_name+'|'+subcat_name))
                        
                        return
                # else:
                #     url = cat1.xpath('@href').string()
                    
                #     print name+'|'+cat1_name, url
                #     session.queue(RequestProds(url, 0), process_prodlist, dict(cat=name+'|'+cat1_name))


# def process_category(data: Response, context: dict[str, str], session: Session):
    
#     print data.content
#     return
    
#     strip_namespace(data)

#     subcats = data.xpath('//section[@id="category-list"]/ul/li/a')
#     for subcat in subcats:
#         subcat_name = subcat.xpath('text()').string()
#         url = subcat.xpath('@href').string()
#         session.queue(Request(url), process_prodlist, dict(cat=context['cat'] + '|' + subcat_name))


def process_prodlist(data: Response, context: dict[str, str], session: Session):
    
    print data.content
    return
    
    strip_namespace(data)

    prods = data.xpath('//a[contains(@class, "product-item-link")]')
    for prod in prods:
        name = prod.xpath('text()').string()
        url = prod.xpath('@href').string()

        if name and url:
            url = 'https://www.underarmour.com/en-us/p/' + url.split('?')[0].split('/')[-1]
            if not session.seen(url):
                session.queue(Request(url), process_product, dict(context, name=name, url=url))

    next_url = data.xpath('//a[contains(text(), "Next")]/@href').string()
    if next_url and not session.seen(next_url):
        session.queue(Request(next_url), process_prodlist, dict(context))


def process_product(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    pr = dict()
    pr['name'] = context['name']
    pr['url'] = context['url'].split('?')[0]
    pr['ssid'] = pr['url'].split('/')[-1].replace('.html', '')
    pr['id.sku'] = pr['ssid']
    pr['category'] = context['cat']
    pr['manufacturer'] = "UnderArmour"

    try:
        prod_json = simplejson.loads(data.xpath('''//script[contains(text(), '"@type": "Product"')]//text()''').string())
        pr['id.manufacturer'] = prod_json.get('sku')
    except:
        pass

    passkey = 'caNcZjVkX1Gk7UMLWxnq0OlhTFyIorng8qNroUp16nHgU'
    displaycode = '2471-en_us'
    locale = 'en_CA,en_US'
    pid = pr['ssid']

    if pid and not session.seen(pid):
        process_reviews_request(data, dict(product=pr, pid=pid, passkey=passkey, locale=locale, displaycode=displaycode), session)
