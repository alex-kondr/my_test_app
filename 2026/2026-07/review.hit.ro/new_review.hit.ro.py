from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.hit.ro/gadgeturi/review.html', use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and url:
            session.queue(Request(url, use='curl'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').split('Review:')[0].split('- Preview')[0].split('review:')[0].split(' Review - ')[0].split(' review - ')[0].split('Review monitor')[-1].split('- Review')[0].split(' - review Hit.ro')[0].split('- REVIEW')[0].split('Review HIT.ro -')[-1].split('Review HIT:')[-1].split('HIT Shop:')[-1].replace('Review-uri la', '').replace('Mini Review', '').split(': prezentare')[0].split('Review HIT.ro:')[-1].split('Test ')[-1].split('Tips:')[-1].split('Tips!')[-1].replace('Review HIT.ro', '').replace('Review', '').split(' review – ')[0].split(' – REVIEW')[0].split(' – Preview')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('--')[-1].replace('.html', '')
    product.category = 'Gadgeturi'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    pros = data.xpath('//strong[contains(., "aspecte pozitive putem")]/following-sibling::text()[preceding-sibling::strong[1][contains(., "aspecte pozitive putem")] and starts-with(., "–")]')
    if not pros:
        pros = data.xpath('(//p[strong[contains(., "Plusuri:")]]/following-sibling::p)[1][br]//text()')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//strong[contains(., "aspectele mai putin")]/following-sibling::text()[preceding-sibling::strong[1][contains(., "aspectele mai putin")] and starts-with(., "–")]')
    if not cons:
        cons = data.xpath('(//p[strong[contains(., "Minusuri:")]]/following-sibling::p)[1][br]//text()')

    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[header]//p[contains(@class, "post-excerpt")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//strong[contains(., "Concluzi")]/following-sibling::text()|(//strong[contains(., "Concluzi")]/following-sibling::a|//strong[regexp:test(., "Concluzi", "i")]/following-sibling::p|//strong[contains(., "Concluzi")]/following-sibling::strong)//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//body//div/p[not(@class)]//text()[not(preceding::strong[contains(., "Concluzi") or contains(., "Plusuri:") or contains(., "Minusuri:")] or regexp:test(., "Concluzi|Specificatii complete|Plusuri:|Minusuri:"))]').string(multiple=True)
    if excerpt:
        excerpt = excerpt.split('Criteriu Nota Plusuri')[0]
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
