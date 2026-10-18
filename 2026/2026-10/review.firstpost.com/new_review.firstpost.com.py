from agent import *
from models.products import *
import simplejson
import re


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:157.0) Gecko/20100101 Firefox/157.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7' -H 'Accept-Encoding: deflate' -H 'Alt-Used: www.firstpost.com' -H 'Connection: keep-alive' -H 'Cookie: cdp_vid=f8339d99-b0b3-4c29-a51b-f86d2c4cc8c8-1791889107185; ppid=f8339d99-b0b3-4c29-a51b-f86d2c4cc8c8-1791889107185; ppid_temp=f8339d99-b0b3-4c29-a51b-f86d2c4cc8c8-1791889107185; _dd_s_v2=aid=a650c9b3-adbd-4fdd-ba8e-9bbac61f7576&id=7f97069b-edc9-4b0d-a997-b612e75e13bd&created=1791889108792&expire=1791890033688&c=0; g_state={"i_l":1,"i_ll":1791889109838,"i_b":"NA+l5L9he07Ecw5vOVP99RXbrFjrJgIrMwr47H61Vd4","i_e":{"enable_itp_optimization":24},"i_et":1791889109838}; gppid=1791889109591-b7b4a793-dc49-407a-8821-42fb1b0f8f80; cdp_tags={"cookies":"https://staticcdp.nw18.com/scripts/e14cc3c0-f5ed-4b5c-8d40-940472638814/1733824772474-userCookies.js","pageview":"https://staticcdp.nw18.com/scripts/e14cc3c0-f5ed-4b5c-8d40-940472638814/1733827677768-userPageView.js","os":"https://staticcdp.nw18.com/scripts/e14cc3c0-f5ed-4b5c-8d40-940472638814/1733824808026-userOS.js","browser":"https://staticcdp.nw18.com/scripts/e14cc3c0-f5ed-4b5c-8d40-940472638814/1733827666916-userBrowser.js","devicetype":"https://staticcdp.nw18.com/scripts/e14cc3c0-f5ed-4b5c-8d40-940472638814/1733824739181-userDeviceType.js"}' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers'"""


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.queue(Request('https://www.firstpost.com/tech/reviews/', use='curl', options=OPTIONS, force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@id, "morestories")]/@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url, use='curl', options=OPTIONS, force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//a[@aria-label="Next page"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', options=OPTIONS, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    title = data.xpath('//h1[contains(@class, "atttl")]/text()').string()

    product = Product()
    product.name = title.split(' Preview ')[0].split(' Review')[0].split(' review:')[0].split(' Preview: ')[0].replace('Review: ', '').replace('Review ', '').replace(' reviewed', '').replace(' review', '').replace('&', ' - ').replace('&#039;', "’").strip()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.html', '')
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = title.replace('&', ' - ').replace('&#039;', "'")
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[contains(span/b/text(), "First Published:")]/span[not(b)]/text()').string()
    if date:
        review.date = date.rsplit(', ', 1)[0]

    try:
        rev_json = data.xpath('//script[@id="__NEXT_DATA__"]/text()').string()
        rev_json = simplejson.loads(rev_json)

        if not date:
            date = rev_json.get('props', {}).get('pageProps', {}).get('pageData', {}).get('pageConfig', {}).get('wdata', {}).get('articleData', {}).get('data', {}).get('created_at')
            if date:
                review.date = date.split()[0]
    except:
        pass

    author = data.xpath('//a[contains(@href, "/author/")]/text()').string(multiple=True)
    author_url = data.xpath('//a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Rating:")]//text()[regexp:test(., "\d.?\d?/\d") and not(contains(., "http:"))]').string()
    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0].split()[-1])
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//strong[contains(., ":") and regexp:test(., "\d.?\d?/\d") and not(contains(., "span style") or .//a or contains(., "Rating:"))]')
    for grade in grades:
        grade = grade.xpath('.//text()').string(multiple=True)
        grade_name = re.split(r'\d\.?\d{0,2}/\d+', grade)[0].split(' - ')[-1].strip('( :)').split(':')[-1].strip()
        grade_val, grade_best = re.search(r'\d\.?\d{0,2}/\d+', grade).group().split('/')
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)))

    pros = data.xpath('//p[strong[contains(., "Pros")]]//text()[not(preceding::strong[contains(., "Cons") or contains(., "Price")] or contains(., "Pros:") or contains(., "Price"))][normalize-space()][starts-with(., "-")]')
    if not pros:
        pros = data.xpath('//p[.//b[contains(., "Pros")]]//text()[not(preceding::strong[contains(., "Cons") or contains(., "Price")] or contains(., "Pros") or contains(., "Price"))][normalize-space()]')
    if not pros:
        pros = data.xpath('//strong[contains(., "Pros")]/following-sibling::span[not(preceding::strong[contains(., "Cons")] or contains(., "Cons"))]//text()')
    if not pros:
        pros = data.xpath('//p[contains(strong, "Pros")]/following-sibling::p[not(preceding-sibling::p[contains(., "Cons")])][starts-with(normalize-space(.), "-")]//text()')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro and '- ' in pro:
            sub_pros = pro.split('- ')
        else:
            sub_pros = pro.split('– ')

        for pro in sub_pros:
            pro = pro.strip(' -–+')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('(//p[contains(strong, "Pros")]/following-sibling::div)[1]//li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.:;•,–►…')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('//strong[contains(., "Cons")]/following-sibling::text()[not(preceding::strong[contains(., "Rating") or contains(., "Price")] or contains(., "[caption id=") or contains(., "Image Credit: Tech2"))][normalize-space()]')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Cons")]]//text()[preceding::strong[1][contains(., "Cons")]][not(preceding::strong[contains(., "Rating") or contains(., "Price")] or contains(., "Cons:") or contains(., "Price"))][normalize-space()][starts-with(., "-")]')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Cons")]]//text()[not(preceding::strong[contains(., "Rating") or contains(., "Price")] or contains(., "Cons") or contains(., "Rating") or contains(., "Price"))][normalize-space()]')
    if not cons:
        cons = data.xpath('//strong[contains(., "Cons")]/following-sibling::span[starts-with(., "-")]//text()')
    if not cons:
        cons = data.xpath('//p[contains(strong, "Cons")]/following-sibling::p[starts-with(normalize-space(.), "-") and not(preceding-sibling::p[contains(strong, "Rating:")])]//text()[starts-with(normalize-space(.), "-")]')

    for con in cons:
        con = con.string(multiple=True)
        if con and '- ' in con:
            sub_cons = con.split('- ')
        else:
            sub_cons = con.split('– ')

        for con in sub_cons:
            con = con.strip(' -–+')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('(//p[contains(strong, "Cons")]/following-sibling::div)[1]//li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.strip(' +-*.:;•,–►…')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    summary = data.xpath('(//h2|//span)[@class="less-cont"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[contains(@class, "outer")]/p[contains(@class, "atsbttl")]//text()').string(multiple=True)

    if summary:
        summary = summary.replace('&mldr;', '...')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//p[strong[regexp:test(., "verdict", "i")]]|//p[strong[regexp:test(., "verdict", "i")]]/following-sibling::p)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[strong[regexp:test(., "conclusion", "i")]]|//p[strong[regexp:test(., "conclusion", "i")]]/following-sibling::p)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//strong[regexp:test(., "verdict", "i")]/following-sibling::text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "verdict", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "Is it worth it?", "i")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        conclusion = re.split(r'[vV]erdict|[cC]onclusion', conclusion)[-1]
        conclusion = re.sub(r'Image.+\[/caption\]', '', conclusion)
        conclusion = re.sub(r'\|.+\[/caption\]', '', conclusion)
        conclusion = re.sub(r'\[caption id=.attachment_\d+. align=.+ width=.\d+.\]', '', conclusion)
        conclusion = conclusion.replace('[/caption]', '').replace('&#039;', "'").strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//p[strong[regexp:test(., "verdict", "i")]]/preceding-sibling::p[not(strong[regexp:test(., "Pros|Cons")] or regexp:test(., "Rating:|Click here for"))]//text()[not(contains(., "Review:") or regexp:test(., "\d.?\d?/\d") or contains(., "Price:"))]|//p[strong[regexp:test(., "verdict", "i")]]//text())[not(starts-with(normalize-space(.), "-") or regexp:test(., "verdict", "i"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p[strong[regexp:test(., "conclusion", "i")]]/preceding-sibling::p[not(strong[regexp:test(., "Pros|Cons")] or regexp:test(., "Rating:|Click here for"))]//text()[not(contains(., "Review:") or regexp:test(., "\d.?\d?/\d") or contains(., "Price:"))]|//p[strong[regexp:test(., "conclusion", "i")]]//text())[not(starts-with(normalize-space(.), "-") or regexp:test(., "conclusion", "i"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[contains(@class, "content")]/p[not(strong[regexp:test(., "Pros|Cons")] or regexp:test(., "Rating:|Click here for"))]//text()[not(contains(., "Review:") or regexp:test(., "\d.?\d?/\d") or contains(., "Price:") or regexp:test(., "conclusion|verdict", "i"))])[not(starts-with(normalize-space(.), "-"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[contains(@class, "artical-main")]/p[not(strong[regexp:test(., "Pros|Cons")] or regexp:test(., "Rating:|Click here for") or preceding::h2[regexp:test(., "verdict|Is it worth it?", "i")])]//text()[not(contains(., "Review:") or regexp:test(., "\d.?\d?/\d") or contains(., "Price:") or regexp:test(., "conclusion|verdict|Here are a few more images:", "i"))])[not(starts-with(normalize-space(.), "-"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "artical-main")]//text()[not(starts-with(normalize-space(.), "-") or parent::strong[regexp:test(., "Pros|Cons|Price:|Rating:")] or parent::figcaption)]').string(multiple=True)

    if excerpt:
        excerpt = re.split(r'\.[\w\s\d,:()]+[vV]erdict|\.[\w\s\d,:()]+[cC]onclusion', excerpt)[0]
        excerpt = re.sub(r'Image.+\[/caption\]', '', excerpt)
        excerpt = re.sub(r'\|.+\[/caption\]', '', excerpt)
        excerpt = re.sub(r'\[caption id=.attachment_\d+. align=.+ width=.\d+.\]', '', excerpt)
        excerpt = excerpt.replace('[/caption]', '').replace('â€™', "'").strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
