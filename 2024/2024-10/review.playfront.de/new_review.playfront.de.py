from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://playfront.de/category/reviews/', force_charset='utf-8'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "blog-wrap")]//div[contains(@class, "p-wrap p-grid")]')
    for rev in revs:
        title = rev.xpath('h3[@class="entry-title"]/a/text()').string()
        url = rev.xpath('h3[@class="entry-title"]/a/@href').string()
        ssid = rev.xpath('@data-pid').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, {})


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Test: ')[-1].split('TEST: ')[-1].split('TEST – ')[-1].split('Kurztest – ')[-1].split(' – ')[0].replace('Review: ', '').replace('Kurztest: ', '').replace('Leser-Review: ', '').replace('PlayLink Kompakttest: ', '').replace('im Review ', '').replace('TEST:', '').replace(u'\u00a0', '').strip(' -')
    product.url = data.xpath('//p/text()[contains(., "Offizielle Homepage:")]/following-sibling::a/@href').string() or data.xpath('//a[span[contains(., "Bei Amazon")]]/@href').string() or context['url']
    product.ssid = context['ssid']
    product.category = 'Hardware' if 'Hardware' in context['title'] else 'Spiele'

    manufacturer = data.xpath('//p/text()[contains(., "Entwickler:")]').string() or data.xpath('//p/text()[contains(., "Publisher:")]').string()
    if manufacturer:
        product.manufacturer = manufacturer.split(':', 1)[-1].split('//', 1)[0]

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//span[contains(@class, "meta-date")]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "meta-author")]/a').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    summary = data.xpath('//p[@class="s-tagline"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    next_url = data.xpath('//span[@class="text-link-next"]/a/@href').string()
    if next_url:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=review.url))

    context['product'] = product
    context['review'] = review

    process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    pros = data.xpath('//div[@class="lets-review-block__pros"]/div[contains(@class, "block__pro")]/text()').strings()
    for pro in pros:
        pro = pro.strip(' -+')
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="lets-review-block__cons"]/div[contains(@class, "block__con")]/text()').strings()
    for con in cons:
        con = con.strip(' -+')
        if con:
            review.add_property(type='cons', value=con)

    grade_overall = data.xpath('//div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    conclusion = data.xpath('//div[contains(@class, "entry-content")]/div//div[@class="lets-review-block__conclusion"]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//blockquote[preceding-sibling::*[self::h2[@id="fazit"] or self::p[.="Fazit" or .="FAZIT"]]] ').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[.="Fazit" or .="FAZIT"]/following-sibling::p[1]//text()[not(contains(., "["))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[@id="fazit"]/following-sibling::blockquote/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)


    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(regexp:test(., "offizielle homepage:", "i") and a)][not(contains(., " // ") or (contains(., "Entwickler") and contains(., ":")))][not(.="Fazit" or .="FAZIT")][not(preceding-sibling::p[.="FAZIT" or .="Fazit"])][not(self::p[contains(., "»") or contains(., ">>")] or contains(., "Die technischen Daten"))]//text()[not(contains(., "[nggallery") or contains(., "[miniflickr") or contains(., "[youtube") or contains(., "[asa") or contains(., "[amazon") or contains(., "Note:"))]').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        context['excerpt'] = context.get('excerpt', '') + excerpt.replace('&nbsp;', ' ').strip()

    next_url = data.xpath('//span[@class="text-link-next"]/a/@href').string()
    if next_url:
        next_page = next_url.split('/')[-2]
        review.add_property(type='pages', value=dict(title=review.title + ' - page ' + next_page, url=next_url))
        session.do(Request(next_url, force_charset='utf-8'), process_review_next, dict(context, review=review))

    elif context.get('excerpt'):
        review.add_property(type="excerpt", value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)