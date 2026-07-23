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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.dkamera.de/testbericht/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//table[@id="tkl_testbericht_uebersicht"]//tbody/tr')
    for rev in revs:
        name = rev.xpath('td[contains(@class, "camera")]/a//text()').string(multiple=True)
        manufacturer = rev.xpath('td[contains(@class, "camera")]/a/strong/text()').string()
        url = rev.xpath('td[contains(@class, "camera")]/a/@href').string()
        prod_url = rev.xpath('td[@class="price"]/a/@href').string()
        date = rev.xpath('td[@class="date"]/text()').string()
        grade_overall = rev.xpath('td[@class="score"]/text()').string()

        if name and url:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(name=name, manufacturer=manufacturer, url=url, prod_url=prod_url, grade_overall=grade_overall, date=date))

    # Load all revs


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.url = context['prod_url'] or context['url']
    product.ssid = context['url'].strip('/').split('/')[-1]
    product.category = "Digitalkameras"
    product.manufacturer = context.get('manufacturer')

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[@id="title"]/a//text()').string()
    review.url = context['url']
    review.ssid = product.ssid
    review.date = context['date']

    grade_overall = context.get('grade_overall')
    if grade_overall:
        grade_overall = grade_overall.strip(' %').replace(',', '.')
        if grade_overall and grade_overall.split('.')[0].isdigit():
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    context['excerpt'] = data.xpath('//div[contains(@class, "testbericht")]/div[contains(@class, "node")]/p[not(@class="teaser-images")][not(preceding::h3[contains(., "Testurteil")])][not(regexp:test(., "Unser Fazit:", "i"))][not(preceding::p[regexp:test(., "Unser Fazit:", "i")])]//text()').string(multiple=True)

    pages = data.xpath('(//select[@class="select-page"])[1]/option')
    if pages:
        for page in pages:
            title = page.xpath('text()').string()
            page_url = 'https://www.dkamera.de' + page.xpath('@value').string()
            review.add_property(type='pages', value=dict(title=title, url=page_url))

        session.do(Request(page_url, use='curl', force_charset='utf-8'), process_review_next, dict(context, product=product, review=review, pages=True))

    else:
        context['review'] = review
        context['product'] = product
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    pros = data.xpath('//ul[@class="pro"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip('*+.-_\n ')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="contra"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip('*+.-_\n ')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[contains(@class, "testbericht")]/div[contains(@class, "node")]/p[not(@class="teaser-images")][not(preceding::h3[contains(., "Testurteil")])][regexp:test(., "Unser Fazit:", "i") or preceding::*[regexp:test(., "Unser Fazit:", "i")]]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('Unser Fazit:', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "testbericht")]/div[contains(@class, "node")]/p[not(@class="teaser-images")][not(preceding::h3[contains(., "Testurteil")])][not(regexp:test(., "Unser Fazit:", "i"))][not(preceding::p[regexp:test(., "Unser Fazit:", "i")])]//text()').string(multiple=True)
    if excerpt:
        context['excerpt'] = context.get('excerpt', '') + excerpt

    if context.get('excerpt'):
        review.add_property(type="excerpt", value=context['excerpt'].strip())

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
