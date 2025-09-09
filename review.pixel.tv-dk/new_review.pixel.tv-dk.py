from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://pixel.tv/category/gaming/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="grid-container-shadow"]')
    for rev in revs:
        title = rev.xpath('.//h3[@class="title"]/text()').string()
        author = rev.xpath('.//p[@class="author"]/text()').string()
        date = rev.xpath('.//p[@class="date"]/text()').string()
        url = rev.xpath(".//a/@href").string()
        session.queue(Request(url), process_review, dict(title=title, author=author, date=date, url=url))

    if revs:
        page = context.get('page', 0) + 1
        url = 'https://pixel.tv/wp-admin/admin-ajax.php'
        options = "--compressed -X POST -H 'X-Requested-With: XMLHttpRequest' --data-raw 'action=load_more_posts&page=" + str(page) + "&category_id=7'"
        session.do(Request(url, use='curl', options=options, force_charset='utf-8', max_age=0), process_revlist, dict(page=page))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = "Gaming"

    product.name = context['title'].split('|')[-1].replace('Anmeldelse: ', '').replace('Anmeldelse', '').replace('anmeldelse', '').strip()
    if '‘' in product.name:
        product.name = product.name.split('‘')[-1].split('’')[0].strip()

    platforme = data.xpath('//strong[contains(., "PLATFORME")]/following-sibling::text()').string()
    if not platforme:
        platforme = data.xpath('//p[contains(., "platforme:")]/text()[2]').string()
    if not platforme or len(platforme) < 2:
        platforme = data.xpath('//b[contains(., "platforme:")]/following-sibling::a/text()').strings()
    if not platforme or len(platforme) < 2:
        platforme = data.xpath('//strong[contains(., "platforme:")]/following-sibling::a/text()').strings()
    if platforme:
        if isinstance(platforme, list):
            platforme = '/'.join(set(platforme))
        product.category = product.category + '|' + platforme.split(':')[-1].replace(' (anmeldt på)', '').replace(', ', '/').replace('|', ',').strip()

    product.category = product.category.rstrip('|')

    manufacturer = data.xpath('//strong[contains(., "UDVIKLER/UDGIVER")]/following-sibling::text()').string()
    if not manufacturer:
        manufacturer = data.xpath('//p[contains(., "Udvikler/Udgiver")]/text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':')[-1].strip()

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    if context['author']:
        review.authors.append(Person(name=context['author'], ssid=context['author']))

    summary = data.xpath('//div[@class="hero-container"]/p/text()').string()
    if summary:
        summary = summary.replace('[…]', '').replace('...', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Konklusion")]/following-sibling::p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Konklusion")]]/following-sibling::p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Konklusion")]/preceding-sibling::p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Konklusion")]]/preceding-sibling::p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Se med på")]/preceding-sibling::p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Nintendo – Pluto TV")]/preceding-sibling::p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[not(@class)]/p[not(contains(., "Udvikler") or contains(., "UDVIKLER") or contains(., "Udgiver") or contains(., "UDGIVER") or contains(., "platforme:") or contains(., "PLATFORME:") or contains(., "Kopi suppleret"))]//text()').string(multiple=True)

    if excerpt:
        if summary and len(excerpt.replace(summary, '').strip()) < 10:
            return

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
