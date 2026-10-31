from agent import *
from models.products import *


XTITLE = ['im Vergleich', 'der Beste']


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.campgarden.de/cg/pages/69092/geraete'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[contains(div/@class, "Internal-Kategorie")]//div[@class="Internal-Name"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url), process_review, dict(title=title, url=url))


def process_review(data: Response, context: dict[str, str], session: Session):
    if (data.xpath('count(//p[contains(., "Mehr Info")])') > 1 
        or data.xpath('count(//p[normalize-space(strong/text())="Vorteile"])') > 1
        or data.xpath('count(//h4[@class="Template-TTITEL"])') > 1):
        return

    product = Product()
    product.name = context['title'].split(' - ')[0].replace('im Test', '').replace('-Langzeittest', '').replace('-Test', '').replace(' Test', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    # no date

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@class, "Artikel")]/p[@class="Template-INTRO"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//h3[contains(., "Fazit")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "Artikel")]/p[not(@class or .//*[contains(@class, "INLINE")] or preceding-sibling::h4)]//text()').string(multiple=True)

    if excerpt:
        conclusion = data.xpath('//h3[contains(., "Fazit")]/following-sibling::p[not(preceding-sibling::h4)]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//p[normalize-space(strong/text())="Ergebnis"]//text()[not(contains(., "Ergebnis"))]').string(multiple=True)
        if not conclusion:
            if 'Das Fazit der Redaktion ist eindeutig:' in excerpt:
                excerpt, conclusion = excerpt.split('Das Fazit der Redaktion ist eindeutig:')
            elif 'Unser Fazit:' in excerpt:
                excerpt, conclusion = excerpt.split('Unser Fazit:')

        if conclusion:
            conclusion = conclusion.replace('Unser Fazit: ', '')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
