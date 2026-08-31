from agent import *
from models.products import *


XTITLE = ['Die besten ', ' vs. ']


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.macwelt.de/tests', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="item-text"]//@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    if any([xtitle in title for xtitle in XTITLE]):
        return

    product = Product()
    product.name = title.split(' im Test')[0].split('Kurztest: ')[-1].split('Test: ')[-1].split(' Produkteinschätzung')[0].replace('-Test', '').replace(' im Praxistest', '').split(' im Doppeltest:')[0].split(' im Vorabtest:')[0].replace('Praxistest: ', '').replace(' im Kurztest', '').split(' im Langzeittest')[0].replace(' (Praxistest)', '').replace('Nachgetestet:', '').replace(' im Vergleichstest', '').replace('Vergleichstest: ', '').replace('Spieletest: ', '').replace('Angetestet: ', '').replace('Test-Update: ', '').replace(' im Akkutest', '').replace('Test ', '').replace(' Test', '').strip()
    product.ssid = context['url'].split('article/')[-1].split('/')[0]

    url = data.xpath('//a/@data-adblocker-link[contains(., "amazon.de/dp/")]').string()
    if url:
        product.url = url.split('?')[0]
    else:
        product.url = context['url']

    product.category = data.xpath('(//li[@class="breadcrumb-item"]/a[not(regexp:test(., "Home|Reviews|Test"))]//text()[normalize-space()])[last()]').string()
    if not product.category:
        product.category = 'Technik'

    review = Review()
    review.type = "pro"
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//div[h1]//div[contains(@class, "card__info--light")]//text()[normalize-space()]').string()

    author_url = data.xpath('//div[@class="author__name"]/a/@href').string()
    author = data.xpath('//div[@class="author__name"]/a/text()').string()
    if not author:
        author = data.xpath('//div[@class="author__name"]/text()').string()

    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.replace('von ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="starRating"]/@style').string()
    if grade_overall:
        grade_overall = grade_overall.split(": ")[-1].strip(' ;')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[h3[@id="pro"]]/ul/li')
    if not pros:
        pros = data.xpath('(//p[contains(., "Pro:")]/following-sibling::*)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h3[@id="kontra"]]/ul/li')
    if not cons:
        cons = data.xpath('(//p[contains(., "Contra:")]/following-sibling::*)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[contains(@class, "subheadline")]//text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//h2[contains(., "Fazit: ")]/following-sibling::p[not(a[contains(., "kaufen")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Sollten Sie das")]/following-sibling::p[not(contains(a, "Amazon ansehen"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p[not(a[contains(., "kaufen")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p/b[contains(., "Fazit")]/parent::p/following-sibling::p[not(a[contains(., "kaufen")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[@class="verdict"]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//*[regexp:test(local-name(), "^h\d+")][@id="fazit"]/following-sibling::p[not(@class="verdict")]//text()').string()

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="article__main"]//div[@class="article-column__content"]/p[not(preceding-sibling::*[1][@class="review-price"] or preceding-sibling::h2[regexp:test(., "Sollten Sie das|Fazit")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//div[@class="article-column__content"]/p[not(preceding-sibling::*[1][@class="review-price"] or preceding-sibling::h2[regexp:test(., "Sollten Sie das|Fazit")])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
