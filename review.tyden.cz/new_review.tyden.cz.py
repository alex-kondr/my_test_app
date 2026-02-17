from agent import *
from models.products import *
import time


SLEEP = 1


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://pctuning.cz/'), process_catlist, dict())
    session.queue(Request('https://pctuning.cz/story/software'), process_revlist, dict(cat="Software"))


def process_catlist(data, context, session):
    time.sleep(SLEEP)

    cats = data.xpath('(//div[span[contains(., "Hardware")]])[1]//ul[@class="header-menu__drawer-list"]//a')
    for cat in cats:
        name = "Hardware" + '|' + cat.xpath('.//text()').string(multiple=True)
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    time.sleep(SLEEP)

    revs = data.xpath('//h2[@class="un-card-headline"]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    time.sleep(SLEEP)

    product = Product()
    product.name = context['title'].replace('Test ', '').replace(' v testu', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat'].replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//p[@class="post-header-info__name"]//text()').string()
    author_url = data.xpath('//p[@class="post-header-info__name"]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-box__rating"]//div/@data-rating').string()
    if grade_overall:
        grade_overall = float(grade_overall) / 10
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('//div[contains(@class, "proscons-pros")]//span[@class="un-list-item__text-secondary"]')
    if not pros:
        pros = data.xpath('//tbody[tr[contains(., "Klady")]]/tr/td[starts-with(normalize-space(.), "+")]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "proscons-cons")]//span[@class="un-list-item__text-secondary"]')
    if not cons:
        cons = data.xpath('//tbody[tr[contains(., "Zápory")]]/tr/td[starts-with(normalize-space(.), "-")]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-body__perex"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="review-box__verdict"]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@class="post-body"]/div[not(@class or .//div or .//img or .//a[contains(@href, "https://levi.cz/")])]|//div[@class="post-body"]/p)//text()').string(multiple=True)

    pages = data.xpath('//div[contains(@class, "post-chapters__section")]//a')
    if pages:
        for page in pages:
            page_title = page.xpath('.//text()').string(multiple=True)
            page_url = page.xpath('@href').string()
            review.add_property(type='pages', value=dict(title=page_title, url=page_url))

        is_conclusion_page = True if 'závěr' in page_title.lower() else False
        session.do(Request(page_url), process_review_last, dict(context, product=product, review=review, excerpt=excerpt, is_conclusion_page=is_conclusion_page))

    elif excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    review = context['review']

    grade_overall = data.xpath('//div[@class="review-box__rating"]//div/@data-rating').string()
    if grade_overall:
        grade_overall = float(grade_overall) / 10
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('//div[contains(@class, "proscons-pros")]//span[@class="un-list-item__text-secondary"]')
    if not pros:
        pros = data.xpath('//tbody[tr[contains(., "Klady")]]/tr/td[starts-with(normalize-space(.), "+")]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "proscons-cons")]//span[@class="un-list-item__text-secondary"]')
    if not cons:
        cons = data.xpath('//tbody[tr[contains(., "Zápory")]]/tr/td[starts-with(normalize-space(.), "-")]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h2[contains(., "Závěr")]/following-sibling::div[not(@class or .//div or .//img or .//a[contains(@href, "https://levi.cz/")])]|//h2[contains(., "Závěr")]/following-sibling::p)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="review-box__verdict"]/p//text()').string(multiple=True)
    if not conclusion and context['is_conclusion_page']:
        conclusion = data.xpath('(//div[@class="post-body"]/div[not(@class or .//div or .//img or .//a[contains(@href, "https://levi.cz/")])]|//div[@class="post-body"]/p)//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "Závěr")]/preceding-sibling::div[not(@class or .//div or .//img or .//a[contains(@href, "https://levi.cz/")])]|//h2[contains(., "Závěr")]/preceding-sibling::p)//text()').string(multiple=True)
    if not excerpt and not context['is_conclusion_page']:
        excerpt = data.xpath('(//div[@class="post-body"]/div[not(@class or .//div or .//img or .//a[contains(@href, "https://levi.cz/")])]|//div[@class="post-body"]/p)//text()').string(multiple=True)

    if excerpt:
        context['excerpt'] += " " + excerpt

    if context['excerpt']:
        if conclusion:
            context['excerpt'] = context['excerpt'].replace(conclusion, '').strip()

        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
