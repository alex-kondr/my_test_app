from agent import *
from models.products import *
import simplejson
import re
import HTMLParser


h = HTMLParser.HTMLParser()
OPTIONS = "--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://www.trendyol.com/en' -H 'Connection: keep-alive' -H 'Cookie: platform=web; anonUserId=d6c244a0-567a-11f0-9e5e-f190a88281d1; __cf_bm=MT9lWAtQeejXvpzfgyPyovS.g.7nUL8G1ZkzthCKLwA-1751375522-1.0.1.1-cIMns0bjYSipgR1QkXef6r2SvyQ4gmX4PyO0S2WHSZFJqdiCzrWBKj734Cpp2UbPHDS_L13NKS21L8gfMc9KR31Q55oQF.QXJZlIndemoqA; __cflb=04dToXpE75gnanWf1Jct5BHNFbbVQqWABMeParAveZ; _cfuvid=G9eMdM7gBhwwI7WuqrrYxhCJuy2y_4r5mOG5onc9h54-1751374603976-0.0.1.1-604800000; navbarGenderId=1; UserInfo=%7B%22Gender%22%3Anull%2C%22UserTypeStatus%22%3Anull%2C%22ForceSet%22%3Afalse%7D; OptanonConsent=isGpcEnabled=0&datestamp=Tue+Jul+01+2025+16%3A12%3A09+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202402.1.0&browserGpcFlag=0&isIABGlobal=false&consentId=e7302f6a-708e-4ef7-a266-2c2fa27f5b7c&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0002%3A1%2CC0009%3A1%2CC0007%3A1%2CC0003%3A1%2CC0001%3A1%2CC0005%3A1%2CC0004%3A1&hosts=&genVendors=V77%3A0%2CV67%3A0%2CV79%3A0%2CV71%3A0%2CV69%3A0%2CV7%3A0%2CV5%3A0%2CV9%3A0%2CV1%3A0%2CV70%3A0%2CV3%3A0%2CV68%3A0%2CV78%3A0%2CV17%3A0%2CV76%3A0%2CV80%3A0%2CV16%3A0%2CV72%3A0%2CV10%3A0%2CV40%3A0%2C&geolocation=DE%3BBE&AwaitingReconsent=false; hvtb=1; VisitCount=1; SearchMode=1; FirstSession=0; OptanonAlertBoxClosed=2025-07-01T12:56:47.757Z; pid=d6c244a0-567a-11f0-9e5e-f190a88281d1; sid=fgbiOj4heO; referrerPageType=homepage; homepageAb=homepage%3AadWidgetSorting_V1_1-componentSMHPLiveWidgetFix_V3_1-firstComponent_V3_1-sorter_V4_b-performanceSorting_V1_3-topWidgets_V1_1%2CnavigationSection%3Asection_V1_1%2CnavigationSideMenu%3AsideMenu_V1_1; WebRecoTss=shopTheLookVersion%2F1%7CcrossRecoAdsVersion%2F1%7CsimilarRecoAdsVersion%2F1%7CallInOneRecoVersion%2F1%7CbasketRecoVersion%2F1%7CcrossRecoVersion%2F4%7CsimilarRecoVersion%2F1%7CcompleteTheLookVersion%2F1%7CpdpGatewayVersion%2F1%7CsimilarSameBrandVersion%2F1%7CcrossSameBrandVersion%2F1%7CcollectionRecoVersion%2F1; AbTestingCookies=A_26-B_85-C_7-D_94-E_90-F_5-G_34-H_17-I_76-J_41-K_29-L_43-M_16-N_86-O_93; _gcl_au=1.1.2040041879.1751374673; tss=firstComponent_V1_1%2Csorter_V1_b%2Csection_V1_1%2CsideMenu_V1_1%2CtopWidgets_V1_1%2CSuggestionTermActive_B%2CDGB_B%2CSB_B%2CSuggestion_C%2CCatTR_B%2CFilterRelevancy_1%2CListingScoringAlgorithmId_1%2CProductCardVariantCount_B%2CProductGroupTopPerformer_B; AwinCookie=; COOKIE_TY.IsUserAgentMobileOrTablet=false; msearchAb=ABAdvertSlotPeriod_1-ABAD_B-ABQR_B-ABqrw_b-ABSimD_B-ABBSA_D-ABSuggestionLC_B; WebAbTesting=A_19-B_73-C_44-D_17-E_20-F_21-G_72-H_76-I_96-J_60-K_65-L_88-M_37-N_19-O_53-P_22-Q_91-R_43-S_69-T_89-U_99-V_20-W_56-X_68-Y_80-Z_55; ForceUpdateSearchAbDecider=forced; WebRecoAbDecider=ABattributeRecoVersion_1-ABcollectionRecoVersion_1-ABshopTheLookVersion_1-ABcrossRecoVersion_1-ABsimilarRecoAdsVersion_1-ABcrossSameBrandVersion_1-ABcompleteTheLookVersion_1-ABallInOneRecoVersion_1-ABbasketRecoVersion_1-ABcrossRecoAdsVersion_1-ABsimilarRecoVersion_1-ABsimilarSameBrandVersion_1-ABpdpGatewayVersion_1; AbTesting=SFWBFP_B-SFWDBSR_A-SFWDQL_B-SFWDRS_A-SFWDSAOFv2_B-SFWDSFAG_B-SFWDTKV2_A-SFWPSCB_B-SFWPSlicerOB_B-SSTPRFL_B-STSBuynow_B-STSCouponV2_A-STSImageSocialProof_A-STSRecoRR_B-STSRecoSocialProof_A%7C1751376999%7Cd6c244a0-567a-11f0-9e5e-f190a88281d1; utmSourceLT30d=direct; utmMediumLT30d=not set; utmCampaignLT30d=not set; userid=undefined; WebAbDecider=ABres_B-ABBMSA_B-ABRRIn_B-ABSCB_B-ABSuggestionHighlight_B-ABBP_B-ABCatTR_B-ABSuggestionTermActive_A-ABAZSmartlisting_62-ABBH2_B-ABMB_B-ABMRF_1-ABARR_B-ABMA_B-ABSP_B-ABPastSearches_B-ABSuggestionJFYProducts_B-ABSuggestionQF_B-ABBadgeBoost_A-ABFilterRelevancy_1-ABSuggestionBadges_B-ABProductGroupTopPerformer_B-ABOpenFilterToggle_2-ABRR_2-ABBS_2-ABSuggestionPopularCTR_B; COOKIE_TY.Anonym=tx=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1cm46dHJlbmR5b2w6YW5vbmlkIjoiNDZmYzFhNGU1NjdkMTFmMDk5Y2VmZTc5NDFiM2MwZDMiLCJyb2xlIjoiYW5vbiIsImF0d3J0bWsiOiI0NmZjMWE0Yi01NjdkLTExZjAtOTljZS1mZTc5NDFiM2MwZDMiLCJhcHBOYW1lIjoidHkiLCJhdWQiOiJzYkF5ell0WCtqaGVMNGlmVld5NXR5TU9MUEpXQnJrYSIsImV4cCI6MTkwOTE2MzY1MSwiaXNzIjoiYXV0aC50cmVuZHlvbC5jb20iLCJuYmYiOjE3NTEzNzU2NTF9.1MevD3GcG9sgEphqyczSHmulzMKB2gO7747pYzmxzCg; storefrontId=1; countryCode=TR; language=tr' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i'"


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.trendyol.com/', use='curl', options=OPTIONS, max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats_json = data.xpath('//script[contains(., "NAVIGATION_APP_INITIAL_STATE")]/text()').string()
    if not cats_json:
        return

    cats = simplejson.loads(cats_json.split('__ = ')[-1]).get('items', [])
    for cat in cats:
        name = cat.get('title')

        sub_cats = cat.get('children', [])
        for sub_cat in sub_cats:
            sub_name = sub_cat.get('title')

            sub_cats1 = sub_cat.get('children', [])
            for sub_cat1 in sub_cats1:
                sub_name1 = sub_cat1.get('title')
                url = 'https://www.trendyol.com' + sub_cat1.get('webUrl') + '?sst=MOST_RATED'
                session.queue(Request(url, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(cat=name+'|'+sub_name+'|'+sub_name1))


def process_prodlist(data, context, session):
    resp = simplejson.loads(data.content)

    prods = resp.get('result', {}).get('products', [])
    for prod in prods:
        product = Product()
        product.name = prod['name']
        product.manufacturer = prod.get('brand', {}).get('name')
        product.url = 'https://www.trendyol.com' + prod['url']
        product.category = prod.get('categoryHierarchy', '').replace('/', '|') or context['cat']
        product.ssid = str(prod['id'])
        product.sku = product.ssid

        # 'https://www.trendyol.com/sayina/kadin-siyah-straplez-cift-halkali-lastik-detayli-astarli-yuksek-bel-sik-deniz-havuz-bikini-takimi-p-715890548/yorumlar?boutiqueId=61&merchantId=381608&sav=true'

        revs_cnt = prod.get('ratingScore', {}).get('totalCount')
        if revs_cnt and revs_cnt > 0:
                        # 'https://apigw.trendyol.com/discovery-web-websfxsocialreviewrating-santral/product-reviews-detailed?&sellerId=381608&contentId=715890548'
            revs_url = 'https://apigw.trendyol.com/discovery-sfint-social-service/api/review/reviews/%s?page=0&pageSize=20' % product.ssid
            session.do(Request(revs_url, use='curl', options=OPTIONS, max_age=0), process_reviews, dict(product=product))

    prods_cnt = resp.get('result', {}).get('totalCount', 0)
    offset = context.get('offset', 0) + 24
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 1
        next_url = data.response_url.split('&pi=')[0] + '&pi=' + str(next_page)
        session.queue(Request(next_url, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(context, offset=offset, page=next_page))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content).get('productReviews', {})

    revs = revs_json.get('content', [])
    for rev in revs:
        if rev.get('language') != 'tr':
            continue

        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))
        review.date = rev.get('commentDateISOType')

        title = rev.get('commentTitle')
        if title:
            review.title = h.unescape(remove_emoji(title)).strip(' ,*_-+\n\t')

        author_name = rev.get('sellerName', rev.get('userFullName'))
        if author_name:
            author_name = h.unescape(remove_emoji(author_name)).strip(' ,*_-+\n\t')
            author_ssid = rev.get('userId')
            if author_name and author_ssid:
                review.authors.append(Person(name=author_name, ssid=str(author_ssid)))
            elif author_name:
                review.authors.append(Person(name=author_name, ssid=author_name))

        is_verified = rev.get('trusted')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('reviewLikeCount')
        if hlp_yes and hlp_yes > 0:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        grade_overall = rev.get('rate')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev.get('comment')
        if excerpt:
            excerpt = h.unescape(remove_emoji(excerpt)).strip(' ,*_-+\n\t')
            if excerpt:
                review.add_property(type='excerpt', value=excerpt)
                product.reviews.append(review)

    revs_cnt = revs_json.get('totalElements', 0)
    offset = context.get('offset', 0) + 20
    if offset < revs_cnt:
        next_page = context.get('page', 0) + 1
                #    'https://apigw.trendyol.com/discovery-web-websfxsocialreviewrating-santral/product-reviews-detailed?&sellerId=381608&contentId=715890548&page=0
        next_url = 'https://apigw.trendyol.com/discovery-sfint-social-service/api/review/reviews/%s?page=%s&pageSize=20' % (product.ssid, next_page)
        session.do(Request(next_url, use='curl', options=OPTIONS, max_age=0), process_reviews, dict(product=product, offset=offset, page=next_page))
    elif product.reviews:
        session.emit(product)
