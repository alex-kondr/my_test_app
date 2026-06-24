from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.ingame.de/suche/?qr=im+Test', force_charset='utf-8'), process_category, dict())


def process_category(data, context, session):
    revs_cnt = data.xpath('//p[contains(@class, "SearchResult")]/strong[regexp:test(., "\d+")]/text()').string()
    if revs_cnt:
        revs_cnt = int(revs_cnt.replace(u'\xa0', '').replace(' ', ''))
        if revs_cnt > 0:
            url = 'https://www.ingame.de/lightweight-ajax.html?qr=im+Test&eventtype=lazyLoadAjaxHandler&lazyLoadData=%7B%22type%22%3A%22PAGING%22%2C%22archiveParam%22%3A%22%22%2C%22categoryId%22%3A1157838%2C%22versionedContainerId%22%3A450221%2C%22cmsTagId%22%3Anull%2C%22showRessortLinkInTeaser%22%3Atrue%2C%22alreadyUsedOnlineIds%22%3A%22%22%2C%22query%22%3A%22index-vc-450221-1%22%7D'
            session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(revs_cnt=revs_cnt))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="id-LinkOverlay-link"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'im Test' in title:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    offset = context.get('offset', 0) + 25
    if offset < context['revs_cnt']:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.ingame.de/lightweight-ajax.html?qr=im+Test&eventtype=lazyLoadAjaxHandler&lazyLoadData=%7B%22type%22%3A%22PAGING%22%2C%22archiveParam%22%3A%22%22%2C%22categoryId%22%3A1157838%2C%22versionedContainerId%22%3A450221%2C%22cmsTagId%22%3Anull%2C%22showRessortLinkInTeaser%22%3Atrue%2C%22alreadyUsedOnlineIds%22%3A%22%22%2C%22query%22%3A%22index-vc-450221-{page}%22%7D'.format(page=next_page)
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context, offset=offset, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('im Test')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1].replace('.html', '')
    product.category = 'Spiele'

    product.manufacturer = data.xpath('//tr[contains(td/text(), "Verlag")]/td[not(contains(., "Verlag"))]/text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//tr[contains(., "Entwickler")]/td[not(contains(., "Entwickler"))]/text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//strong[contains(., "Entwickler:")]/following-sibling::text()[normalize-space(.)]').string()

    platforms = data.xpath('//tr[contains(td, "Plattformen")]/td[not(contains(., "Plattformen"))]/text()').string()
    if platforms:
        product.category += '|' + platforms.replace('|', '\\').replace(', ', '/')

    genres = data.xpath('//tr[contains(., "Genre")]/td[not(contains(., "Genre"))]/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    if not platforms and not genres:
        product.category = 'Technik'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//a[contains(@class, "authors")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "authors")]/@href').string()
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
    if not cons:
        cons = data.xpath('//tbody[tr[contains(., "Con")]]/tr[not(contains(., "Con"))]/td[2]')

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
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Für wen lohnt sich der")]/following-sibling::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Fazit", "i")]/preceding::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Fazit")]]/preceding::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Für wen lohnt sich der")]/preceding::p[@class="id-StoryElement-paragraph"]//text()').string(multiple=True)
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
