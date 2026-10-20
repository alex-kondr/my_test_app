from agent import *
from models.products import *


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
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://bgr.com/reviews/", use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "article")]/h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'the best ' not in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    if revs:
        offset = context.get('offset', 0) + len(revs)
        next_url = 'https://www.bgr.com/category/reviews/?ajax=1&offset={}&action=more-stories'.format(offset)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(offset=offset))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review:')[0].split(' review:')[0].split(' Review')[0].split(' review')[0].split(' review: ')[0].replace('Tested: ', '').replace('Review: ', '').strip()
    product.ssid = data.xpath('//h1/@data-post-id').string()
    product.manufacturer = data.xpath('//tr[th[regexp:test(., "Brand", "i")]]/td/text()').string()

    product.url = data.xpath('//table[contains(., "Buy From")]//td/a/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@class, "buy-button")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('//ul[contains(@class, "breadcrumbs")]/li/a[not(regexp:test(normalize-space(.), "^Reviews|Tech|News", "i"))]/text()').string()
    if category:
        product.category = category.replace('Reviews', '').strip()
    else:
        product.category = 'Tech'

    mpn = data.xpath('//tr[th[regexp:test(., "^\s*ASIN", "i")]]/td/text()').string()
    if mpn:
        product.add_property(type='id.manufacturer', value=mpn)

    ean = data.xpath('//tr[th[regexp:test(., "Identification Number", "i") or regexp:test(., "upc", "i")]]/td/text()').string()
    if ean and ean.isdigit():
        product.add_property(type='id.ean', value=ean)

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[contains(@class, "timestamp")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@property="article:author"]/@content').string()
    author_url = data.xpath('//a[@class="byline-author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating"]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//span[@class="score-number"]/text()').string()

    if grade_overall:
        grade_overall = grade_overall.split('/')[0].split(': ')[-1].replace(',', '.')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=10.0))

    pros = data.xpath('//*[@class="pro"]//li')
    if not pros:
        pros = data.xpath('//ul[@class="pros"]/li')
    if not pros:
        pros = data.xpath('(//*[@class="pro"]/following-sibling::ul)[1]//li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//*[@class="con"]//li')
    if not cons:
        cons = data.xpath('//ul[@class="cons"]/li')
    if not cons:
        cons = data.xpath('(//*[@class="con"]/following-sibling::ul)[1]//li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="top"]//div[@class="review-desc"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="dc-description"]//p//text()').string(multiple=True)

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@id="content"]//p[preceding::h2[regexp:test(@id, "^h-conclusion") or regexp:test(., "wrap-up") or regexp:test(., "conclusion") or regexp:test(., "^h-should-you") or regexp:test(., "^\s*Conclusion", "i")]][not(@class="disclaimer" or @class="sc-description" or contains(., "This is a sponsored article"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@id="content"]//p[not(ancestor::div[contains(@class, "detailed-commerce")])][not(@class="disclaimer" or @class="sc-description" or contains(., "This is a sponsored article"))][not(preceding::h2[regexp:test(@id, "^h-conclusion") or regexp:test(., "wrap-up") or regexp:test(., "conclusion") or regexp:test(., "^h-should-you") or regexp:test(., "^\s*Conclusion", "i")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
