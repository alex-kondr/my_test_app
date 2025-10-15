from agent import *
from models.products import *
import time


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request("https://androidinsider.ru/", max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath("//ul[@id='menu-trendy']/li/a")
    for cat in cats:
        name = cat.xpath("text()").string()
        url = cat.xpath("@href").string()
        session.queue(Request(url, max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    prods = data.xpath("//h2[@class='post-title']/a")
    for prod in prods:
        name = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        session.queue(Request(url, max_age=0), process_product, dict(context, name=name, url=url))

    next_page = data.xpath("//a[@rel='next']/@href").string()
    if next_page:
        session.queue(Request(next_page, max_age=0), process_revlist, dict(context))


def process_product(data, context, session):
    product = Product()
    product.name = context["name"]
    product.ssid = context["url"].split('/')[-1].split('.')[0]
    product.category = context["cat"]

    product.url = data.xpath('//a[@class="link-alert"]/@href').string()
    if not product.url:
        product.url = context["url"]

    review = Review()
    review.type = "pro"
    review.title = product.name
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath("//time/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[contains(@class, 'author-name')]//text()").string(multiple=True)
    author_url = data.xpath("//a[contains(@class, 'author-name')]/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath("//div[@class='article-body']//h2[regexp:test(., 'Выводы')]/following-sibling::p[.//text()[string-length(normalize-space(.))>100]][1]//text()[string-length(normalize-space(.))>0]").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Стоит ли")][last()]/following-sibling::p[not(a[@class="link-alert"])]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Стоит ли")][last()]/preceding-sibling::p[not(a[@class="link-alert"] or code)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-body"]/p[not(.//a[regexp:test(@href, "://dzen.ru/|://t.me/")])]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)

        time.sleep(10)
