from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.natursidan.se/tester/', force_charset="utf-8"), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="Teaser-body"]/parent::li/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset="utf-8", max_age=0), process_review, dict(context, url=url))

    next_url = data.xpath('//div[contains(@class,"ContentItemList-items")]//a/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset="utf-8"), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    title = data.xpath('//h1[contains(@class,"ContentHead-heading")]//text()').string()

    product = Product()
    product.name = title.replace('Bokrecension: ', '').replace('Recension av ', '').replace('Recension: ', '').replace('Test: ', '').replace('Test av ', '')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = data.xpath('//a[@class="Label ContentHead-contextPrimary"]/text()').string()

    review = Review()
    review.type = "pro"
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="ContentHead-meta"]/time/@datetime').string()
    if date:
        review.date = date.split("T")[0]

    author = data.xpath('//div[@class="Bylines-names"]/a/text()').string()
    author_url = data.xpath('//div[@class="Bylines-names"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, url=author_url))

    grade_overall = data.xpath('//strong[regexp:test(text(),"Betyg: \d")]/text()').string(multiple=True)
    grade_overall = re_search_once(r'(\d+) av', grade_overall)
    if grade_overall:
        review.grades.append(Grade(value=float(grade_overall), best=5.0, worst=0, type='overall'))

    # pros = data.xpath('//div[@class="Body"]//p//text()[regexp:test(normalize-space(.),"^\+ ")]').strings()
    # for pro in pros:
    #     pro = pro.replace('+', '').strip()
    #     if len(pro) > 1:
    #         review.add_property(type="pros", value=pro)

    # cons = data.xpath('//div[@class="Body"]//p//text()[regexp:test(normalize-space(.),"^– ")]').strings()
    # for con in cons:
    #     con = con.replace('–', '').strip()
    #     if len(con) > 1:
    #         review.add_property(type="cons", value=con)

    conclusion = data.xpath('//div[@class="Body"]//p[regexp:test(strong/text(),"SAMMANFATTNING:")]//text()[not(ancestor::strong[regexp:test(text(),"SAMMANFATTNING:")])]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="Body"]//strong[contains(text(), "Avslutningsvis")]/parent::p/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="Body"]//strong[contains(text(), "Slutsats")]/parent::p/text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="Body"]/p[not(regexp:test(strong, "SAMMANFATTNING:|Avslutningsvis|Slutsats"))]/text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
