from agent import *
from models.products import *
import time


XTITLE = ['digitest - ', ' vs. ']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.digimanie.cz/recenze/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2//a')

    if not revs and not context.get('repeat'):
        time.sleep(1)
        session.do(Request(data.response_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(repeat=True))
        return

    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if url and title and not any(xtitle in title.lower() for xtitle in XTITLE):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' v testu', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-v-testu', '')
    product.category = data.xpath('//div[@class="post-header-info__content"]//a[not(contains(., "Recenze"))]/text()[normalize-space(.)]').string() or 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//p[contains(@class, "info__name")]//text()').string(multiple=True)
    author_url = data.xpath('//p[contains(@class, "info__name")]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div/@data-rating').string()
    if grade_overall:
        grade_overall = float(grade_overall) / 10
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//h2[contains(., "Plusy")]/following-sibling::p[starts-with(normalize-space(.), "+")]|//div[contains(@class, "proscons-pros")]//span[contains(@class, "text")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h2[contains(., "Minusy")]/following-sibling::p[starts-with(normalize-space(.), "-")]|//div[contains(@class, "proscons-cons")]//span[contains(@class, "text")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-body__perex"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="post-body"]/p[not(preceding::h2[regexp:test(., "Plusy|Minusy|vhodný pro|Závěr")] or regexp:test(., "\[\_heureka|\(klikněte pro zvětšení\)|\d+\. ISO"))]//text()').string(multiple=True)

    pages = data.xpath('//div[@class="post-chapters__section"]//a')
    for page in pages:
        title = page.xpath('text()').string()
        url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=url))

    if pages:
        session.do(Request(url, use='curl', force_charset='utf-8'), process_review_last, dict(product=product, review=review, excerpt=excerpt))

    elif excerpt:
        conclusion = data.xpath('//h4[contains(., "Verdikt")]/following-sibling::p//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//h2[contains(., "Závěr")]/following-sibling::p//text()').string(multiple=True)

        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    review = context['review']

    grade_overall = data.xpath('//div/@data-rating').string()
    if grade_overall:
        grade_overall = float(grade_overall) / 10
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//h2[contains(., "Plusy")]/following-sibling::p[starts-with(normalize-space(.), "+")]|//div[contains(@class, "proscons-pros")]//span[contains(@class, "text")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//h2[contains(., "Minusy")]/following-sibling::p[starts-with(normalize-space(.), "-")]|//div[contains(@class, "proscons-cons")]//span[contains(@class, "text")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Závěr")]/following-sibling::p[not(preceding::h2[regexp:test(., "Plusy|Minusy|vhodný pro")] or regexp:test(., "\[\_heureka|\(klikněte pro zvětšení\)|\d+\. ISO"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="post-body"]/p[not(preceding::h2[regexp:test(., "Plusy|Minusy|vhodný pro")] or regexp:test(., "\[\_heureka|\(klikněte pro zvětšení\)|\d+\. ISO"))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Závěr")]/preceding-sibling::p[not(preceding::h2[regexp:test(., "Plusy|Minusy|vhodný pro|Závěr")] or regexp:test(., "\[\_heureka|\(klikněte pro zvětšení\)|\d+\. ISO"))]//text()').string(multiple=True)
    if excerpt:
        context['excerpt'] += ' ' + excerpt

    excerpt = context['excerpt']
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
