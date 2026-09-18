from agent import *
from models.products import *
import simplejson


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.natursidan.se/tester/', force_charset="utf-8"), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="Teaser-body"]/parent::li/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset="utf-8"), process_review, dict(context, url=url))

    next_url = data.xpath('//div[contains(@class,"ContentItemList-items")]//a/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset="utf-8"), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    resp_html = data.xpath('//script[@type="application/ld+json"]/text()').string()
    data_json = simplejson.loads(resp_html)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//a[@class="Label ContentHead-contextPrimary"]/text()').string()

    review = Review()

    title = data.xpath('//h1[contains(@class,"ContentHead-heading")]//text()').string()
    if title:
        product.name = title.replace('Bokrecension: ', '').replace('Recension av ', '').replace('Recension: ', '').replace('Test: ', '').replace('Test av ', '')

    review.title = title
    review.ssid = product.ssid
    review.date = data_json['datePublished'].split('T')[0]
    review.type = "pro"
    review.url = product.url

    author_name = data_json['author'][0].get('name')
    author_url = data_json['author'][0].get('url')
    if author_name and author_url:
        review.authors.append(Person(name=author_name, ssid=author_name, url=author_url))

    grade_overall = data.xpath('//strong[regexp:test(text(),"Betyg: \d")]/text()').string(multiple=True)
    grade_overall = re_search_once(r'(\d+) av', grade_overall)
    if grade_overall:
        review.grades.append(Grade(value=float(grade_overall), best=5.0, worst=0, type='overall'))

    cons = data.xpath('//div[@class="Body"]//p//text()[regexp:test(normalize-space(.),"^–")]').strings()
    for con in cons:
        con = con.replace('–', '').strip()
        if con:
            review.properties.append(ReviewProperty(type="cons", value=con))

    pros = data.xpath('//div[@class="Body"]//p//text()[regexp:test(normalize-space(.),"^\+")]').strings()
    for pro in pros:
        pro = pro.replace('+', '').strip()
        if pro:
            review.properties.append(ReviewProperty(type="pros", value=pro))

    conclusion = data.xpath('//div[@class="Body"]//p[regexp:test(strong/text(),"SAMMANFATTNING:")]//text()[not(ancestor::strong[regexp:test(text(),"SAMMANFATTNING:")])]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="Body"]//strong[contains(text(), "Avslutningsvis")]/parent::p/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="Body"]//strong[contains(text(), "Slutsats")]/parent::p/text()').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type="conclusion", value=conclusion))

    summary = data.xpath('//div[@class="Body"]/p[1]/strong/text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type="summary", value=summary))

    excerpt = data.xpath('//div[@class="Body"]/p/text()')
    excerpt = ' '.join([f.string() for f in excerpt if not (f.string().startswith('–') or f.string().startswith('•') or f.string().startswith('+') or f.string().startswith(':') )])
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

    product.reviews.append(review)
    session.emit(product)