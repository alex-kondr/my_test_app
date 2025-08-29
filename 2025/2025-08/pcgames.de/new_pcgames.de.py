from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()



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
    session.queue(Request('https://www.pcgames.de/Artikel-Archiv/Tests/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "cal_years")]/a/@href')
    for cat in cats:
        url = cat.string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_catlist_next, dict())


def process_catlist_next(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//div[contains(@class, "cal_day")]/a/@href')
    for cat in cats:
        url = cat.string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "Pagination_right")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Games'

    product.name = data.xpath('//span[contains(@class, "productTitle")]//text()').string(multiple=True) or context['title'].split(': Blu-ray-Test ')[0].replace(' im Blu-ray-Test', '').replace(' - Review/Filmkritik', '').replace(' --- Filmkritik / Review', '').replace(' (Review / Filmkritik)', '').replace(' (Review/Filmkritik)', '').replace(' (Review/Fimkritik)', '').replace('(Filmkritik/Review)', '').replace(' - Kinokritik/Review', '').replace(' - Filmkritik/Review', '').replace(' (Kinokritik/Review)', '').replace(' im Test', '').replace('Review: ', '').replace(' - Kinoreview & Trailer', '').replace(' - Großes Review', '').replace(' - Review', '').replace(' (Kinokritik / Review)', '').replace(' (Review/Kinokritik)', '').replace(': Kinokritik/Review', '').replace(' (Kino-Kritik/Review)', '').replace(' (Blu-ray-Kritik / Review)', '').replace(' (Kinokritik/ Review)', '').replace(' (Kritik / Review)', '').strip()
    product.name = h.unescape(product.name).replace(u'\x91', '').replace(u'\x92', '').replace(u'\x93', '').replace(u'\x96', '').replace(u'\x80', '').replace(u'\x82', '').replace(u'\x84', '').strip()

    product.url = data.xpath('//a[contains(., "ZUM ANGEBOT")]/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('//ul[@id="productNavigation"]/li//text()[normalize-space(.)]').join('/')
    if platforms:
        product.category += '|' + platforms

    review = Review()
    review.type = 'pro'
    review.title = context['title'] or data.xpath('//h1[@class="articleTitle"]//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="authorName"]/text()').string()
    author_url = data.xpath('//span[contains(@class, "authors")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="ratingData"]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall)
        grade_overall = grade_overall / 10 if grade_overall > 10 else grade_overall
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//span[contains(@class, "ratingPro")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[contains(@class, "ratingContra")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@class, "artIntro")]//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).replace(u'\x91', '').replace(u'\x92', '').replace(u'\x93', '').replace(u'\x96', '').replace(u'\x80', '').replace(u'\x82', '').replace(u'\x84', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="ratingBox"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="content txtMuted"]//text()').string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion).replace(u'\x91', '').replace(u'\x92', '').replace(u'\x93', '').replace(u'\x96', '').replace(u'\x80', '').replace(u'\x82', '').replace(u'\x84', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    context['excerpt'] = data.xpath('//section[contains(@class, "articleMainTextModule")]/p[not(.//img or preceding::span[contains(., "Fazit")])]//text()|//section[contains(@class, "articleMainTextModule")]/p/text()|//section[contains(@class, "articleMainTextModule")]/p/em/text()').string(multiple=True)

    next_url = data.xpath('//a[contains(@class, "pagRight")]/@href').string()

    pages = data.xpath('//ol[contains(@class, "pgnTitles")]/li/a')
    for page in pages:
        title = page.xpath('span[not(contains(., "Seite "))]/text()').string()
        page_url = page.xpath('@href').string()
        review.add_property(type='pages', value=dict(title=title, url=page_url))

    if pages:
        session.do(Request(page_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, review=review, product=product))

    elif next_url:
        title = review.title + ' - Pagina 1'
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, page=2, review=review, product=product))

    elif context['excerpt']:
        excerpt = h.unescape(context['excerpt']).replace(u'\x91', '').replace(u'\x92', '').replace(u'\x93', '').replace(u'\x96', '').replace(u'\x80', '').replace(u'\x82', '').replace(u'\x84', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    page = context.get('page', 0)
    if page:
        title = review.title + ' - Pagina ' + str(page)
        page += 1
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

    grade_overall = data.xpath('//span[@class="ratingData"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//span[contains(@class, "ratingPro")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[contains(@class, "ratingContra")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="ratingBox"]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="content txtMuted"]//text()').string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion).replace(u'\x91', '').replace(u'\x92', '').replace(u'\x93', '').replace(u'\x96', '').replace(u'\x80', '').replace(u'\x82', '').replace(u'\x84', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//section[contains(@class, "articleMainTextModule")]/p[not(.//img or preceding::span[contains(., "Fazit")])]//text()|//section[contains(@class, "articleMainTextModule")]/p/text()|//section[contains(@class, "articleMainTextModule")]/p/em/text()').string(multiple=True)
    if excerpt:
        context['excerpt'] += ' ' + excerpt

    next_url = data.xpath('//a[contains(@class, "pagRight")]/@href').string()
    if next_url:
        session.do(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_review_next, dict(context, page=page, review=review))

    elif context['excerpt']:
        excerpt = h.unescape(context['excerpt']).replace(u'\x91', '').replace(u'\x92', '').replace(u'\x93', '').replace(u'\x96', '').replace(u'\x80', '').replace(u'\x82', '').replace(u'\x84', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
