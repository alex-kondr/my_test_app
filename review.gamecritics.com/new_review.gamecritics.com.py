from agent import *
from models.products import *
import re


def clean_text(text):
    return text.replace('UAB Å IAULIÅ²', u'UAB ŠIAULIŲ').replace('escrutÃ­nio', u'escrutínio').replace(u'Ã¼', u'ü').replace(u'Ã©', u'é').replace('Ã§', u'ç').replace('bÅ', u'bō').replace('dÃ©jÃ', u'déjà').replace('Ã¨', u'è').replace('Ã¶', u'ö').replace('Ã¡', u'á').replace('Ã±', u'ñ').replace('Ã¯', u'ï').replace('Ãº', u'ú').replace('Ã³', u'ó').replace('Ã¢', u'â').replace('Ãª', u'ê').replace('Ã«', u'ë').replace('Ã£', u'ã').replace('Å²', u'Ų').replace('Ã¤', u'ä').replace('Ã¥', u'å').replace('ï¿½', "'").replace('Ãµ', u'õ').strip()


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://gamecritics.com/tag/game-reviews/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h3[contains(@class, "entry-title")]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = clean_text(context['title']).replace('SVG REVIEW:', '').replace('PREVIEW ', '').replace(' — Review', '').replace(' Review', '').replace(' review', '').strip(' –.')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author")]/a/text()').string()
    author_url = data.xpath('//span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Rating")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = re.search(r'Rating.+\d+\.?\d?', grade_overall)
        if grade_overall:
            grade_overall = grade_overall.group(0).replace('Rating', '').split(':', 1)[-1].strip().split()[0].split('/')[0].replace(',', '.')
            if grade_overall and grade_overall[0].isdigit():
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//p[b[contains(., "HIGH")]]//text()[not(contains(., "HIGH"))]').string(multiple=True)
    if not pros:
        pros = data.xpath('//p[strong[contains(., "HIGH")]]//text()[not(contains(., "HIGH"))]').string(multiple=True)

    if pros:
        pros = clean_text(pros).strip(' +-*.:;•,–')
        if len(pros) > 1:
            review.add_property(type='pros', value=pros)

    cons = data.xpath('//p[b[contains(., "LOW")]]//text()[not(contains(., "LOW"))]').string(multiple=True)
    if not cons:
        cons = data.xpath('//p[strong[contains(., "LOW")]]//text()[not(contains(., "LOW"))]').string(multiple=True)

    if cons:
        cons = clean_text(cons).strip(' +-*.:;•,–')
        if len(cons) > 1:
            review.add_property(type='cons', value=cons)

    summary = data.xpath('//h2[@class]//text()').string(multiple=True)
    if summary:
        summary = clean_text(summary)
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//p[contains(., "Disclosures")]|//p[contains(., "Disclosures")]/following-sibling::p)//text()[not(contains(., ":"))]').string(multiple=True)
    if conclusion:
        conclusion = clean_text(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]//p[not(strong/text()="HIGH" or strong/text()="LOW" or strong/text()="WTF" or b[regexp:test(., "HIGH|LOW|WTF|:")] or preceding-sibling::p[contains(., "Disclosures")] or contains(., "Disclosures") or contains(strong, "Rating:"))]//text()[not(contains(., "Rating:"))]').string(multiple=True)
    if excerpt:
        excerpt = clean_text(excerpt)
        if len(excerpt) > 2:
            if conclusion:
                excerpt = excerpt.replace(conclusion, '').strip()

            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
