from agent import *
from models.products import *
import simplejson
import re


OPTIONS = "--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Referer: https://www.trendyol.com/de' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Connection: keep-alive' -H 'Cookie: platform=web; __cf_bm=Oq1AIZG6qCf4qXsybmspKixnuai89EMT.t02CnDowII-1740660733-1.0.1.1-LwYkE_eGEpz7KWDU5b_gmMxtGSkZChtZdRIWc.Eu00QJX59oPoW3jGySBV_7FwlRBIbEfvy_HK5ZqHRYv4mfJw; __cflb=04dToXpE75gnanWf1Jct5BHNFbbVQqW7qv6252nYLD; _cfuvid=HfYBQiOTbFyAQdmspbwTPYZafxgw7XRSqhnOUJcd0nI-1740660733681-0.0.1.1-604800000; anonUserId=aa9fe0d0-f509-11ef-8adb-cf304ebea9ff; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Feb+27+2025+14%3A53%3A15+GMT%2B0200+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%B8%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202402.1.0&browserGpcFlag=0&isIABGlobal=false&consentId=d575c297-49ed-4338-b1e9-859031aea1ec&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0002%3A1%2CC0009%3A1%2CC0007%3A1%2CC0003%3A1%2CC0001%3A1%2CC0004%3A1&hosts=H138%3A1%2CH29%3A1%2CH111%3A1%2CH129%3A1%2CH93%3A1%2CH128%3A1%2CH112%3A1%2CH147%3A1%2CH148%3A1%2CH56%3A1%2CH58%3A1%2CH59%3A1%2CH91%3A1%2CH20%3A1%2CH104%3A1%2CH115%3A1%2CH75%3A1%2CH86%3A1%2CH25%3A1%2CH90%3A1%2CH32%3A1%2CH116%3A1%2CH124%3A1%2CH7%3A1%2CH152%3A1%2CH37%3A1%2CH42%3A1%2CH43%3A1%2CH153%3A1%2CH149%3A1%2CH145%3A1%2CH134%3A1%2CH139%3A1%2CH144%3A1&genVendors=V77%3A1%2CV67%3A1%2CV79%3A1%2CV71%3A1%2CV69%3A1%2CV7%3A1%2CV5%3A1%2CV9%3A1%2CV1%3A1%2CV70%3A1%2CV3%3A1%2CV68%3A1%2CV78%3A1%2CV17%3A1%2CV76%3A1%2CV80%3A1%2CV16%3A1%2CV72%3A1%2CV10%3A1%2CV40%3A1%2C&geolocation=GB%3BLND&AwaitingReconsent=false; OptanonAlertBoxClosed=2025-02-27T12:52:27.511Z; pid=aa9fe0d0-f509-11ef-8adb-cf304ebea9ff; sid=Y5wIfHSfKG; WebRecoTss=pdpGatewayVersion%2F1%7CcrossRecoAdsVersion%2F1%7CbasketRecoVersion%2F1%7CcompleteTheLookVersion%2F1%7CshopTheLookVersion%2F1%7CsimilarRecoAdsVersion%2F1%7CcrossRecoVersion%2F1%7CsimilarRecoVersion%2F1%7CcollectionRecoVersion%2F1%7ChomepageVersion%2Fsorter%3AhomepageSorterNewTest_b.firstComponent%3AinitialNewTest_1(M)%7CnavigationSectionVersion%2Fsection%3AazSectionTest_1(M)%7CnavigationSideMenuVersion%2FsideMenu%3AinitialTest_1(M); AbTestingCookies=A_72-B_46-C_37-D_12-E_43-F_90-G_24-H_57-I_16-J_98-K_93-L_28-M_9-N_86-O_65; navbarGenderId=1; tss=SuggestionTermActive_B%2CDGB_B%2CSB_B%2CSuggestion_C%2CCatTR_B%2CFilterRelevancy_1%2CListingScoringAlgorithmId_1%2CProductCardVariantCount_B%2CProductGroupTopPerformer_B; UserInfo=%7B%22Gender%22%3Anull%2C%22UserTypeStatus%22%3Anull%2C%22ForceSet%22%3Afalse%7D; _gcl_au=1.1.2107085723.1740660768; AwinCookie=; hvtb=1; VisitCount=1; SearchMode=1; WebAbTesting=A_71-B_71-C_76-D_47-E_38-F_46-G_77-H_1-I_90-J_2-K_14-L_97-M_84-N_23-O_15-P_76-Q_71-R_21-S_30-T_95-U_3-V_82-W_35-X_32-Y_1-Z_12; ForceUpdateSearchAbDecider=forced; WebRecoAbDecider=ABbasketRecoVersion_1-ABcollectionRecoVersion_1-ABcrossRecoVersion_1-ABsimilarRecoAdsVersion_1-ABsimilarSameBrandVersion_1-ABcompleteTheLookVersion_1-ABattributeRecoVersion_1-ABcrossRecoAdsVersion_1-ABsimilarRecoVersion_1-ABcrossSameBrandVersion_1-ABpdpGatewayVersion_1-ABshopTheLookVersion_1-ABhomepageVersion_sorter%3AhomepageSorterNewTest_b.componentHPBuyAgain%3ABuyAgainTest_b.firstComponent%3AinitialNewTest_1.performanceSorting%3AwidgetPerformanceFreqV1_3%28M%29-ABnavigationSideMenuVersion_sideMenu%3AinitialTest_1%28M%29-ABnavigationSectionVersion_section%3AazSectionTest_1%28M%29; msearchAb=ABAdvertSlotPeriod_1-ABCA_A-ABSearchFETestV1_B-ABBSA_D-ABSuggestionLC_B; AbTesting=SFWDBSR_A-SFWDQL_B-SFWDRS_B-SFWDSAOFv2_B-SFWDSFAG_B-SFWDTKV2_A-SSTPRFL_B-STSBuynow_B-STSCouponV2_A-STSImageSocialProof_A-STSRecoRR_B-STSRecoSocialProof_A-STSSocialProofRR_B-WCOrdResRedesign_B-WCSideBarBasketQS_B-WCSideBrBsHide_B%7C1740662559; FirstSession=0; storefrontId=34; countryCode=GB; language=en; referrerPageType=homepage; functionalConsent=true; performanceConsent=true; targetingConsent=true'"


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
    session.queue(Request('https://www.trendyol.com/', use='curl', options=OPTIONS, max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats_json = data.xpath('''//script[contains(., '"title":"Popular Brands"')]/text()''').string()
    if not cats_json:
        return

    cats = simplejson.loads(cats_json.split('PROPS"]=')[-1]).get('data', [])
    cats = [cat for cat in cats if 'Categories' in cat.get('title')][0].get('elements', [])
    for cat in cats:
        name = cat.get('displayName')
        url = 'https://www.trendyol.com' + cat.get('path') + '?sst=MOST_RATED'
        session.queue(Request(url, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(cat=name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@data-testid="product-card"]')
    for prod in prods:
        name = prod.xpath('.//span[@class="product-name-text"]/text()').string()
        brand = prod.xpath('.//span[@class="product-brand"]/text()').string()
        url = prod.xpath('a[@data-testid="product-url"]/@href').string()

        revs_cnt = prod.xpath('.//span[contains(@class, "total-rating-count")]/text()')
        if revs_cnt:
            session.queue(Request(url, use='curl', options=OPTIONS, max_age=0), process_product, dict(context, name=name, brand=brand, url=url))
        else:
            return

    prods_cnt = data.xpath('//div/@data-dr-totalcount').string()
    offset = context.get('offset', 0) + 24
    if prods_cnt and offset < int(prods_cnt):
        next_page = context.get('page', 1) + 2
        next_url = data.response_url.split('&pi=')[0] + '&pi={}'.format(next_page)
        session.queue(Request(next_url, use='curl', options=OPTIONS, max_age=0), process_prodlist, dict(context, offset=offset, page=next_page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = context['cat']
    product.manufacturer = context['brand']

    sku = data.xpath('//div[@data-testid="barcode-no"]/text()').string()
    if sku:
        product.sku = sku.split()[-1]

    revs_url = 'https://apigw.trendyol.com/discovery-sfint-social-service/api/review/reviews/{}?page=0&pageSize=20'.format(product.ssid)
    session.do(Request(revs_url, max_age=0), process_reviews, dict(product=product))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content).get('productReviews', {})

    revs = revs_json.get('content', [])
    for rev in revs:
        review = Review()
        review.type = 'user'
        review.url = product.url
        review.ssid = str(rev.get('id'))
        review.date = rev.get('commentDateISOType')

        author = rev.get('userFullName')
        author_ssid = rev.get('userId')
        if author and author_ssid:
            review.authors.append(Person(name=author, ssid=str(author_ssid)))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.get('rate')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        is_verified = rev.get('trusted')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        hlp_yes = rev.get('reviewLikeCount')
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))

        title = rev.get('commentTitle')
        excerpt = rev.get('originalComment')
        if excerpt and len(remove_emoji(excerpt).strip(' +-.\n\t')) > 1:
            if title:
                review.title = remove_emoji(title)
        else:
            excerpt = title

        if excerpt:
            excerpt = remove_emoji(excerpt).strip(' +-.\n\t')
            if len(excerpt) > 1:
                review.add_property(type='excerpt', value=excerpt)

                product.reviews.append(review)

    revs_cnt = revs_json.get('totalElements', 0)
    offset = context.get('offset', 0) + 20
    if offset < revs_cnt:
        next_page = context.get('page', 0) + 1
        next_url = 'https://apigw.trendyol.com/discovery-sfint-social-service/api/review/reviews/{ssid}?page={page}&pageSize=20'.format(ssid=product.ssid, page=next_page)
        session.do(Request(next_url, max_age=0), process_reviews, dict(product=product, offset=offset, page=next_page))

    elif product.reviews:
        session.emit(product)
