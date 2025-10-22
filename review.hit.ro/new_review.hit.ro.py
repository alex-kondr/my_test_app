from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.hit.ro/gadgeturi/review.html'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        if title and url:
            session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(., "chevron_right")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split('Review:')[0].split('- Preview')[0].split('review:')[0].split(' Review - ')[0].split(' review - ')[0].split('Review monitor')[-1].split('- Review')[0].split(' - review Hit.ro')[0].split('- REVIEW')[0].split('Review HIT.ro -')[-1].split('Review HIT:')[-1].split('HIT Shop:')[-1].replace('Review-uri la', '').replace('Mini Review', '').split(': prezentare')[0].split('Review HIT.ro:')[-1].split('Test ')[-1].split('Tips:')[-1].split('Tips!')[-1].replace('Review HIT.ro', '').replace('Review:', '').replace('Review', '').strip()
    product.url = context['url']
    product.category = 'Gadgeturi'
    product.ssid = product.url.split('--')[-1].replace('.html', '')

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.type = 'pro'
    review.ssid = product.ssid

    date = data.xpath('//div[@class="card-content"]/span[contains(., "calendar")]/text()').string()
    if date:
        review.date = date.split(',')[0]

    author = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"][div[@class="left mr-10"]]//text()[regexp:test(., "\[autor:", "i")]').string()
    if author:
        author = author.split(':')[-1].strip(' ]')
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="card-content"]//text()[regexp:test(., "finala:", "i")]').string()
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].replace(',', '.').strip())
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    summary = data.xpath('//div[@class="card-content"]/p/b[1 or 2]/text()').string()
    if not summary:
        summary = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"]/font[1]/*[1][self::strong]/text()').string()

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"]//text()[preceding::strong[regexp:test(., "concluzi.{0,10}:", "i") or regexp:test(., "^\s*concluzi", "i")]]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"][div[@class="left mr-10"]]//text()[preceding::strong[regexp:test(., "concluzi.{0,10}:", "i") or regexp:test(., "^\s*concluzi", "i")]]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"]/*[self::p or self::font]//text()[not(regexp:test(., "\[autor:", "i") or contains(., "youtube.com") or regexp:test(., "\(clic pe", "i") or regexp:test(., "^\s*SPECIFICATII", "i") or preceding-sibling::text()[regexp:test(., "^\s*SPECIFICATII")])][not(regexp:test(., "finala:", "i"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"]/font//text()[not(preceding::strong[regexp:test(., "concluzi.{0,10}:", "i") or regexp:test(., "^\s*concluzi", "i")])][not(parent::li)][not(regexp:test(., "\[autor:", "i") or regexp:test(., "\(clic pe", "i") or regexp:test(., "^\s*Specificatii", "i") or regexp:test(., "concluzi", "i") or regexp:test(., "sursa:", "i") or regexp:test(., "\<\<", "i") or regexp:test(., "\>\>", "i") or contains(., "youtube.com"))][not(regexp:test(., "finala:", "i"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="card"][.//span[contains(., "calendar")]]/div[@class="card-content"][div[@class="left mr-10"]]//text()[not(preceding::strong[regexp:test(., "concluzi.{0,10}:", "i") or regexp:test(., "^\s*concluzi", "i")])][not(parent::li)][not(regexp:test(., "\[autor:", "i") or regexp:test(., "\(clic pe", "i") or regexp:test(., "^\s*Specificatii", "i") or regexp:test(., "concluzi", "i") or regexp:test(., "sursa:", "i") or regexp:test(., "\<\<", "i") or regexp:test(., "\>\>", "i") or contains(., "youtube.com"))][not(regexp:test(., "finala:", "i"))]').string(multiple=True)

    if excerpt:
        if summary and summary in excerpt:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion and conclusion in excerpt:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
