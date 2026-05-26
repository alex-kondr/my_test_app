from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://guitar.com/reviews/page/1", use="curl", max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[h2 and a]')
    if not revs:
        return

    for rev in revs:
        title = rev.xpath('h2/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use="curl", max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(., "Next") or contains(., "Read More")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context["title"].split(' review: ')[0].split(' review – ')[0].strip()
    product.url = context["url"]
    product.ssid = product.url.split('/')[-2]
    product.category = 'Guitars'
    product.manufacturer = data.xpath('//div[contains(h3, "Related Brands")]/div/a/text()').string()

    review = Review()
    review.type = 'pro'
    review.title = context["title"]
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//div[contains(@title, "Published ")]/text()').string()

    author = data.xpath('//div[contains(span/text(), "by")]/a[contains(@href, "/author/")]/text()').string()
    author_url = data.xpath('//div[contains(span/text(), "by")]/a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//h4[contains(., "Our rating")]/following-sibling::h4/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//span[contains(text(), "⊕")]/following-sibling::text()[1]')
    for pro in pros:
        pro = pro.string()
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[contains(text(), "&ominus;")]/following-sibling::text()[1]')
    for con in cons:
        con = con.string()
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="w-full"]/div/p/text()').string()
    if not summary:
        summary = data.xpath('//meta[@name="description"]/@content').string()

    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "hould I buy")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[contains(., "verdict")]/following-sibling::div/text()[not(following-sibling::br)]').string()

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "hould I buy")]/preceding-sibling::p[not(regexp:test(normalize-space(.), "^[\$\£\€][\w\d]+"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Verdict")]/preceding-sibling::p[not(regexp:test(normalize-space(.), "^[\$\£\€][\w\d]+"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "prose prose-lg")]/p[not(regexp:test(normalize-space(.), "^[\$\£\€][\w\d]+"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
