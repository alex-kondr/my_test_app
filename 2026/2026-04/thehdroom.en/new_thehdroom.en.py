from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request("https://thehdroom.com/gaming/"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//h2/a")
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, url=url, title=title))

    next_url = data.xpath('//a[contains(., "Older ")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Hands-On Preview (Xbox 360, PS3)', '').replace('Hands-On Preview: ', '').replace('Hands-On Preview of ', '').replace(': Hands-On Preview', '').split("Review")[0].split('’ ')[0].split(' Trailer ')[0].split(' Preview: ')[0].split(' Preview ')[0].replace(' Preview', '').strip("''‘’– ")
    product.ssid = context["url"].split("/")[-2].split("-")[-1]
    product.category = 'Gaming'

    product.url = data.xpath('//p[contains(., "Source: ")]/a/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "Purchase the")]/@href').string()
    if not product.url:
        product.url = data.xpath('//p[contains(., "Pre-order")][.//a]//@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "Learn more about")]/@href').string()
    if not product.url:
        product.url = data.xpath('//p[contains(., "Amazon.com")][.//a]//@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "Click here to")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath("//meta[@itemprop='datePublished']/@content").string()
    if not date:
        date = data.xpath('//meta[contains(@property, "published_time")]/@content').string()
    if date:
        review.date = date.split("T")[0]

    author = data.xpath('//div[@class="author"]/a').first()
    if author:
        name = author.xpath("text()").string()
        url = author.xpath("@href").string()
        review.authors.append(Person(name=name, ssid=name, profile_url=url))

    grade_overall = data.xpath('//div[@class="score"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

    conclusion = data.xpath('//p[contains(b, "The Verdict")]/following-sibling::p[not(contains(., "This review was based off"))][not(contains(., "This review is based on"))][not(contains(@id, "caption-attachment"))][not(.//a[contains(., "Purchase the")])][not(.//a[contains(., "Learn more about")])][not(self::p[contains(., "Source:")][.//a])][not(self::p[contains(., "Pre-order")][.//a])][not(self::p[contains(., "Click here to")][.//a])][not(contains(., "This review is based off"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'Ã¤', u'ä').replace(u'Ã¢â‚¬™', u"'").replace(u'Ã¼', u'ü').replace(u'Â¼', u'1/4')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[contains(b, "The Verdict")]/preceding-sibling::p[not(contains(., "This review was based off"))][not(contains(., "This review is based on"))][not(contains(@id, "caption-attachment"))][not(.//a[contains(., "Purchase the")])][not(.//a[contains(., "Learn more about")])][not(self::p[contains(., "Source:")][.//a])][not(self::p[contains(., "Pre-order")][.//a])][not(self::p[contains(., "Click here to")][.//a])][not(contains(., "This review is based off"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]//p[not(contains(., "This review was based off"))][not(contains(., "This review is based on"))][not(contains(@id, "caption-attachment"))][not(.//a[contains(., "Purchase the")])][not(.//a[contains(., "Learn more about")])][not(self::p[contains(., "Source:")][.//a])][not(self::p[contains(., "Pre-order")][.//a])][not(self::p[contains(., "Click here to")][.//a])][not(contains(., "This review is based off"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'Ã¤', u'ä').replace(u'Ã¢â‚¬™', u"'").replace(u'Ã¼', u'ü').replace(u'Â¼', u'1/4')
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
