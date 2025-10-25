from agent import *
from models.products import *


XCAT = ['All']
OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Connection: keep-alive' -H 'Cookie: AMCV_9AE0F0145936E3790A495CAA%40AdobeOrg=179643557%7CMCIDTS%7C20377%7CMCMID%7C83783301265780481336339867931853413773%7CMCOPTOUT-1760545247s%7CNONE%7CvVersion%7C5.5.0; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Oct+15+2025+17%3A20%3A47+GMT%2B0300+(%D0%B7%D0%B0+%D1%81%D1%85%D1%96%D0%B4%D0%BD%D0%BE%D1%94%D0%B2%D1%80%D0%BE%D0%BF%D0%B5%D0%B9%D1%81%D1%8C%D0%BA%D0%B8%D0%BC+%D0%BB%D1%96%D1%82%D0%BD%D1%96%D0%BC+%D1%87%D0%B0%D1%81%D0%BE%D0%BC)&version=202509.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=295cbf0f-9e97-4dc4-a7f1-476b33a0be08&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&GPPCookiesCount=1&groups=BG2705%3A1%2CC0001%3A1%2CC0003%3A1%2CC0002%3A1%2CC0004%3A1%2CC0005%3A1&AwaitingReconsent=false&geolocation=UA%3BKV; OTGPPConsent=DBABLA~BVQqAAAAAABY.QA; gig_bootstrap_3_2vPgUSj6HQdI6ojpyGRTsCAGISJzYaF3V2-EbojfZHwjrE4-V6s4Xa9BFFaOmDjG=login_ver4; _pcid=%7B%22browserId%22%3A%22mc0cpg3cy3d57q3u%22%7D; _pctx=%7Bu%7DN4IgrgzgpgThIC4B2YA2qA05owMoBcBDfSREQpAeyRCwgEt8oBJAEzIEYOAWDgTgDsAZgBsAgEwAOAKwcRk7tyHSQAXyA; xbc=%7Bkpcd%7DChBtYzBjcGczY3kzZDU3cTN1Egp6VWthanZXSjA0Gjw5M0I1VjN3eVJqYjRiWGpWT0NOTTduOTFMeWxBSXlFaUs3aHNTV2FDOG5MSUlNQ2wxSVc1VVlXWUtXQ2kgAA; _pc_usUser=false; OptanonAlertBoxClosed=2025-10-15T14:20:47.378Z; LANG=en_US; __ds_loc_country=UA; __ds_loc_state=KV; usprivacy=1---; AMCVS_9AE0F0145936E3790A495CAA%40AdobeOrg=1; OptanonControl=ccc=UA&csc=KV&cic=0&otvers=202509.1.0&pctm=2025-10-15T14%3A20%3A35.920Z&reg=global&ustcs=1---&tos=0&ds=2&td=0&vers=4.2.5; __pid=.golfdigest.com; __pat=-14400000; __pvi=eyJpZCI6InYtbWdzMnVtczlqcXJiOGl5NyIsImRvbWFpbiI6Ii5nb2xmZGlnZXN0LmNvbSIsInRpbWUiOjE3NjA1MzgwNDgyNDN9; LANG_CHANGED=en_US; __pil=en_US; AKA_A2=A; __tbc=%7Bkpcd%7DChBtYzBjcGczY3kzZDU3cTN1Egp6VWthanZXSjA0Gjw5M0I1VjN3eVJqYjRiWGpWT0NOTTduOTFMeWxBSXlFaUs3aHNTV2FDOG5MSUlNQ2wxSVc1VVlXWUtXQ2kgAA' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.golfdigest.com/equipment/hot-list', use='curl', force_charset='utf-8', options=OPTIONS), process_catlist, dict())
    session.queue(Request('https://www.golfdigest.com/hot-list-2023/', use='curl', force_charset='utf-8', options=OPTIONS), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//div[a[contains(text(), "Hot List")]]/div/ul/li/a')
    if not cats:
        cats = data.xpath('//a[span[contains(@class, "Card__a-Title")]]')

    for cat in cats:
        name = cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//a[@class="o-ClubInfoBox__m-Details"]')
    if not revs:
        revs = data.xpath('//div[contains(@class, "ReviewList") and not(.//p[contains(., "Next")])]/a')

    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS), process_review, dict(context, url=url))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = data.xpath('//h1[regexp:test(@class, "AssetTitle|productTitle")]//text()').string(multiple=True)
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Golf Clubs|' + context['cat']
    product.manufacturer = data.xpath('//h2[@class="brand"]/text()').string()

    product.url = data.xpath('//a[contains(@class, "buy-link")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = context['url']
    review.ssid = product.ssid

    date_info = data.xpath('//script[contains(., "origPubDate =")]/text()').string()
    if date_info:
        review.date = date_info.split("origPubDate = '")[-1].split('T')[0]

    grade_overall = data.xpath('//span[contains(@class, "RatingDisplay--rating")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//div[@class="o-Rating" and .//h6]')
    for grade in grades:
        grade_name = grade.xpath('.//h6/text()').string()
        grade_val = grade.xpath('@data-score').string()
        if not grade_val:
            grade_val = grade.xpath('div/@aria-label').string()

        grade_val = grade_val.split(' out ')[0].split(' of ')[0]
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[h2[contains(., "Why We Like It")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    summary = data.xpath('//div[@class="productDescription"]/p//text()[not(regexp:test(., "WHAT IT DOES|WHY WE LIKE IT|Read more|WHAT YOU NEED TO KNOW"))]').string(multiple=True)

    next_url = data.xpath('//a[contains(text(), "Read more")]/@href').string()
    if next_url:
        if summary:
            review.add_property(type='summary', value=summary)

        session.do(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS), process_review_next, dict(product=product, review=review))
        return

    if summary:
        review.add_property(type='excerpt', value=summary)

        product.reviews.append(review)

    revs = data.xpath('//section[contains(@class, "m-Feedback")]')
    for rev in revs:
        review = Review()
        review.type = 'pro'
        review.title = product.name
        review.url = context['url']
        review.ssid = product.ssid

        author = rev.xpath('following-sibling::div[1]//span[contains(@class, "a-Name")]/text()').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following-sibling::div[1]//span[contains(@class, "Handicap")]/text()').string()
        if grade_overall:
            grade_overall = grade_overall.replace('Handicap', '')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=15.0))

        excerpt = rev.xpath('following-sibling::div[2]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

    if product.reviews:
        session.emit(product)


def process_review_next(data, context, session):
    review = context['review']

    review.title = data.xpath('//h1[regexp:test(@class, "AssetTitle|productTitle")]//text()').string(multiple=True)
    review.date = data.xpath('//div[contains(@class, "AssetPublishDate")]//text()').string(multiple=True)

    author = data.xpath('//span[contains(@class, "a-Name")]//text()').string(multiple=True)
    author_url = data.xpath('//span[contains(@class, "a-Name")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "articleBody")]/div/p[not(regexp:test(., "PRICE:|RELATED:"))]//text()[not(regexp:test(., "WHAT IT DOES|WHY WE LIKE IT|Read more|WHAT YOU NEED TO KNOW"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
