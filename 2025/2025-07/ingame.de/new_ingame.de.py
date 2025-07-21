from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.ingame.de/tests', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())
    session.queue(Request('https://www.ingame.de/tests/reviews-sti1259318/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="id-LinkOverlay-link"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

# no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' im Test')[0].split(' – ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.html', '')
    product.category = 'Spiele'

    product.manufacturer = data.xpath('//tr[contains(., "Entwickler")]/td[not(contains(., "Entwickler"))]/text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//strong[contains(., "Entwickler:")]/following-sibling::text()[normalize-space(.)]').string()

    platfoms = data.xpath('//tr[contains(., "Plattformen")]/td[not(contains(., "Plattformen"))]/text()').string()
    if platfoms:
        product.category += '|' + platfoms.replace(', ', '/')

    genres = data.xpath('//tr[contains(., "Genre")]/td[not(contains(., "Genre"))]/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//a[@class="id-Story-authors-link lp_west_author"]/text()').string()
    author_url = data.xpath('//a[@class="id-Story-authors-link lp_west_author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('-')[-1].replace('.html', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//td[starts-with(normalize-space(.), "+")]')
    if not pros:
        pros = data.xpath('//tbody[tr[contains(., "Pro")]]/tr[not(contains(., "Pro"))]/td[1]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[starts-with(normalize-space(.), "-")]')
    if not cons:
        cons = data.xpath('//tbody[tr[contains(., "Contra")]]/tr[not(contains(., "Contra"))]/td[2]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="id-StoryElement-leadText"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Fazit", "i")]/following-sibling::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Fazit")]]/following-sibling::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Fazit", "i")]/preceding::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Fazit")]]/preceding::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)

    if excerpt:
        if 'Mein Fazit: ' in excerpt:
            excerpt, conclusion = excerpt.split('Mein Fazit: ')
            review.add_property(type='conclusion', value=conclusion.strip())
        elif 'Fazit: ' in excerpt:
            excerpt, conclusion = excerpt.split('Fazit: ')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
