from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.delamar.de/testberichte/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//article[@class]/a|//article[@class]/p[@class="m-b-0"]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Testbericht', '').replace(' Test', '').strip()
    product.ssid = context['url'].split('/')[-2]

    product.url = data.xpath('//a[contains(@class, "shop_button") or contains(., "Check Amazon") or contains(., "Check Thomann")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[@class="row col-md-12 breadcrumbs"]//a[not(h1 or contains(., "Musiksoftware"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    manufacturer = data.xpath('//div[span[contains(., "Hersteller: ")]]//text()').string(multiple=True)
    if manufacturer:
        product.manufacturer = manufacturer.replace('Hersteller:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//meta[@name="date"]/@content').string()

    author = data.xpath('//div[contains(@class, "author")]/div[contains(., "Von")]/text()').string()
    if author:
        author = author.split('am')[0].replace('Von', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating_number"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('count(//span[@class="fa fa-star"])')
        grade_overall_half = data.xpath('count(//span[contains(@class, "fa-star-half")])')
        if grade_overall:
            if grade_overall_half:
                grade_overall += grade_overall_half / 2

            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//ul[@class="pro"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="contra"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="article_teaser"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "fazit")]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "verdict")]/p[@class="m-b-1"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="row"]/div/p[not(@class or audio or video)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
