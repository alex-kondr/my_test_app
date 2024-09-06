from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://techtest.org/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "entry-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2]

    product.name = data.xpath('//div[regexp:test(@class, "^lets-review-block__title")]//text()').string(multiple=True)
    if not product.name:
        product.name = context['title'].split('Ladegerät Test 2024:')[0].split('im Test')[0].replace('Test:', '').split(':')[0].split(' – ')[0].replace('von Techtest', '').replace('und getestet', '').replace('getestet', '').strip()

    product.url = data.xpath('//a[contains(., "Link zum Hersteller")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = data.xpath('(//div[contains(@class, "tdb-category")])[1]/a[not(text()="Tests")]/text()').string()
    if not category:
        category = data.xpath('//li[@class="entry-category"]/a[not(text()="Tests")]/text()').string()
    if category:
        product.category = category.replace('von Techtest', '').replace('Techtest intern', '').replace('Tests', '').replace('Reviews', '').strip()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="tdb-author-name"]/text()').string()
    author_url = data.xpath('//a[@class="tdb-author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    pros = data.xpath('//div[regexp:test(@class, "lets-review-block__pro$")]')
    if not pros:
        pros = data.xpath('//div[@class="aawp-product__description"]//span[@style="color: #339966;"]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[regexp:test(@class, "lets-review-block__con$")]')
    if not cons:
        cons = data.xpath('//div[@class="aawp-product__description"]//span[@style="color: #ff6600;"]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="tdb-block-inner td-fix-index"]/p[not(preceding-sibling::div[@id="ez-toc-container"])]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p[preceding-sibling::div[@id="ez-toc-container"]]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[b[contains(., "Fazit")]]/preceding-sibling::p[not(b)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    conclusion = data.xpath('//h2[contains(., "Fazit")][last()]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[b[contains(., "Fazit")]]/text()|//p[b[contains(., "Fazit")]]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

        product.reviews.append(review)

        session.emit(product)
