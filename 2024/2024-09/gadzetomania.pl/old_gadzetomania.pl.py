from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://gadzetomania.pl/gadzety,temat,6008941124117121?strona=1"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//h2/a")
    for rev in revs:
        name = rev.xpath("@title").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="prev"][contains(@href, "strona=")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.category = "Gadżety"
    product.ssid = product.url.split('/')[-1].split(',')[-1]
    if not product.ssid:
        product.ssid = product.url.split('/')[-1].split(',')[0].replace("%20", '-')

    product.name = context['name'].split("TEST ")[-1].split(" – test")[0].split(" - test")[0].split(" – recenzja")[0].split(" - recenzja")[0].split(" - testujemy ")[0].split(" - słuchawki ")[0].split(" – polskie słuchawki ")[0].split(" - polskie słuchawki ")[0].split(" – mobilny")[0].split(" - mobilny")[0].split(" - te świetnie słuchawki ")[0].split(" - rewelacyjn")[0].split(" - trudno ")[0].split(':')[0].split('(test)')[0].split('już w Polsce')[0].split(' - ')[0].split(' – ')[0]

    review = Review()
    review.title = context["name"]
    review.url = product.url
    review.ssid = product.ssid
    date = data.xpath('//meta[contains(@property, "published_time")]/@content').string()
    if date:
        review.date = date.split('T')[0]
    review.type = "pro"

    author = data.xpath("//a[contains(@href, ',autor,')]").first()
    if author:
        author_name = author.xpath("@title").string()
        author_url = author.xpath("@href").string()
        author_ssid = author_url.split('autor,')[-1]
        if not author_ssid:
            author_ssid = author_name
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
    elif not author:
        author = data.xpath('//meta[@property="og:article:author"]/@content').string()
        if author:
            review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="QXeb"][1]//p/text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type="summary", value=summary.strip()))

    excerpt = data.xpath('//div[@class="DLmz"]//p[not(@class="CXkh P-et CXjr")][not(contains(., "Źródło:"))]//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary.strip(), '', 1).strip()
        if not excerpt:
            excerpt = summary

        review.add_property(type="excerpt", value=excerpt)
        product.reviews.append(review)
        session.emit(product)
