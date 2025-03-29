from agent import *
from models.products import *


XCATS = ['Home', 'Services']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.expertentesten.de/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="mobile-menu"]//a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCATS:
            session.queue(Request(url), process_catlist, dict(cat=name))


def process_catlist(data, context, session):
    sub_cats = data.xpath('//div[@class="kat-item"]')
    for sub_cat in sub_cats:
        sub_name = sub_cat.xpath('h3//text()').string(multiple=True)
        url = sub_cat.xpath('a/@href').string()
        session.queue(Request(url), process_revlist, dict(cat=context['cat'] + '|' + sub_name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="recent_tests_container"]//div[@class="content_container"]')
    for rev in revs:
        name = rev.xpath('.//a/text()').string()
        title = rev.xpath('h3/text()').string()
        url = rev.xpath('.//a/@href').string()
        session.queue(Request(url), process_review, dict(context, name=name, title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['name'].replace(' Test', '')
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//time/@datetime').string()

    author = data.xpath('//span[@class="author-name"]/text()').string()
    author_url = data.xpath('//a[@class="v3-author-button"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="entry_header"]/p/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusions_ = []
    conclusion = data.xpath('//h2[contains(., "Fazit")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(text(), "Fazit")]]/following-sibling::p[1]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(text(), "Fazit")]]//text()').string(multiple=True)
    if not conclusion:
        conclusions = data.xpath('//h3[contains(text(), "Fazit")]')
        for cons in conclusions:
            h2_cnt = cons.xpath('count(following-sibling::p[1]/preceding-sibling::h2)')
            cons = cons.xpath('following-sibling::p')
            for con in cons:
                if con.xpath('count(preceding-sibling::h2)') == h2_cnt:
                    con = con.xpath('.//text()').string(multiple=True)
                    if con:
                        conclusions_.append(con)
                else:
                    break
        conclusion = ' '.join(conclusions_)

    if conclusion:
        conclusion = conclusion.replace('Fazit:', '').replace('Fazit', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::strong/text()|//h2[contains(., "Fazit")]/preceding-sibling::p//text()|//h2[contains(., "Fazit")]/preceding-sibling::text()|//h2[contains(., "Fazit")]/preceding-sibling::div[@class="pane"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Links")]/preceding-sibling::strong/text()|//h2[contains(., "Links")]/preceding-sibling::p//text()|//h2[contains(., "Links")]/preceding-sibling::text()|//h2[contains(., "Links")]/preceding-sibling::div[@class="pane"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="main"]/p[not(contains(., "http"))]//text()|//div[@class="main"]/text()|//div[@class="main"]//div[@class="pane"]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('Fazit:', '').replace('Fazit', '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        conclusions = data.xpath('//p[strong[contains(text(), "Fazit")]]/following-sibling::p[1]')
        for con in conclusions:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                excerpt = excerpt.replace(con, '')

        for con in conclusions_:
            excerpt = excerpt.replace(con, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
