from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request("http://www.pointgphone.com/tests-android/", use="curl",  force_charset="utf-8"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="post-link"]')
    for rev in revs:
        title = rev.xpath("h2/text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use="curl", force_charset="utf-8"), process_review, dict(url=url, title=title))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset="utf-8"), process_revlist, dict())


def process_review(data, context, session):
    reviews = data.xpath("//h4[(.//span[contains(.,'Points forts')])]")
    if len(reviews) >= 1:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['url'].split("/")[-2].split("-")[-1]
    product.category = data.xpath("//div[@class='penci-entry-categories']/span[@class='penci-cat-links']//text()").string() or "Tests et Dossiers"

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split("T")[0]

    author = data.xpath('//a[@class="author-name"]/text()').string()
    author_url = data.xpath("//a[@rel='author-name']/@href").string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit


def process_reviews(data, context, session):
    revs = data.xpath('//h3[not(@class) and following::h4[(.//span[contains(.,"Points forts")])]]')
    for i, rev in enumerate(revs, start=1):
        product = Product()
        product.name = rev.xpath('text()').string()
        product.url = context['url']
        product.ssid = product.name.lower().replace(' ', '-')
        product.category = data.xpath("//div[@class='penci-entry-categories']/span[@class='penci-cat-links']//text()").string() or "Tests et Dossiers"

        review = Review()
        review.type = 'pro'
        review.url = product.url
        review.ssid = product.ssid
        review.title = context['title']

        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split("T")[0]

        author = data.xpath('//a[@class="author-name"]/text()').string()
        author_url = data.xpath("//a[@rel='author-name']/@href").string()
        if author and author_url:
            review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('')

        excerpt = rev.xpath('following-sibling::p[count(preceding-sibling::h3)={}][not(contains(., "link="))]//text()'.format(i))