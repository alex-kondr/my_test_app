from agent import *
from models.products import *
import re


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.eurogamer.de/reviews', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "link link--expand")]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[span[@aria-label="Nächste Seite"]]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' im Test ')[0].split(' im Test: ')[0].split(' - Test: ')[0].split(' Test - ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = 'Spiele'

    platforms = data.xpath('//li[contains(., "Plattformen:")]//text()').string(multiple=True)
    if platforms:
        product.category += '|' + re.sub(r'\(.+\)', '', platforms.replace('Plattformen:', '').strip().replace(', ', '/')).strip()

    manufacturer = data.xpath('//li[regexp:test(., "Entwickler:|Hersteller:")]//text()').string(multiple=True)
    if manufacturer:
        product.manufacturer = manufacturer.replace('Entwickler:', '').replace('Hersteller:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author"]/a/text()').string()
    author_url = data.xpath('//span[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
    grade_best = data.xpath('//div[@class="review_rating"]//*[contains(@class, "max_value")]/text()').string()
    if grade_overall:
        grade_best = float(grade_best) if grade_best else 5.0
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=grade_best))

    pros = data.xpath('(//tr[contains(.,"PRO")]/following-sibling::tr//ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//tr[contains(.,"CONTRA")]/following-sibling::tr//ul)[2]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="strapline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//p[strong[regexp:test(., "Conclusion|Fazit")]]|//h2[regexp:test(., "Conclusion|Fazit")])/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//section[@class="synopsis"]/div//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//p[strong[regexp:test(., "Conclusion|Fazit")]]|//h2[regexp:test(., "Conclusion|Fazit")])/preceding::p[not(@class or parent::aside[@class="aside right"])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body_content")]//p[not(@class or parent::aside[@class="aside right"])]//text()').string(multiple=True)

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        title = review.title + " - Pagina 1"
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(grade_overall=grade_overall, excerpt=excerpt, review=review, product=product, page=2))

    else:
        if excerpt and conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        context['excerpt'] = excerpt
        context['review'] = review
        context['product'] = product

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        if not context.get('grade_overall'):
            grade_overall = data.xpath('//div[@class="review_rating"]/@data-value').string()
            grade_best = data.xpath('//div[@class="review_rating"]//*[contains(@class, "max_value")]/text()').string()
            if grade_overall:
                grade_best = float(grade_best) if grade_best else 5.0
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=grade_best))

        pros = data.xpath('(//tr[contains(.,"PRO")]/following-sibling::tr//ul)[1]/li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.strip(' +-*.:;•–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

        cons = data.xpath('(//tr[contains(.,"CONTRA")]/following-sibling::tr//ul)[2]/li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.strip(' +-*.:;•–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

        if data.xpath('//a[contains(@href, "?page=") and regexp:test(., "Conclusion|Verdict|Fazit")]/@href').string() == data.response_url:
            conclusion = data.xpath('//div[contains(@class, "body_content")]//p[@class or pnot(parent::aside[@class="aside right"])]//text()').string(multiple=True)
            if conclusion:
                review.add_property(type='conclusion', value=conclusion)
        else:
            conclusion = data.xpath('(//p[strong[regexp:test(., "Conclusion|Fazit")]]|//h2[regexp:test(., "Conclusion|Fazit")])/following-sibling::p//text()').string(multiple=True)
            if not conclusion:
                conclusion = data.xpath('//div[contains(@class, "body_content")]/div[not(@class)]//text()').string(multiple=True)

            if conclusion:
                review.add_property(type='conclusion', value=conclusion)

            excerpt = data.xpath('(//p[strong[regexp:test(., "Conclusion|Fazit")]]|//h2[regexp:test(., "Conclusion|Fazit")])/preceding::p[not(@class or parent::aside[@class="aside right"])]//text()').string(multiple=True)
            if not excerpt:
                excerpt = data.xpath('//div[contains(@class, "body_content")]/p[not(@class or parent::aside[@class="aside right"])]//text()').string(multiple=True)

            if excerpt:
                context['excerpt'] += " " + excerpt

                if conclusion:
                    context['excerpt'] = context['excerpt'].replace(conclusion, '').strip()

    next_url = data.xpath('//div[@class="next"]/a/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, page=page + 1))

    elif context['excerpt']:
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
