from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.queue(Request("https://techguysmartbuy.com/category/review", use='curl'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(title=title, url=url))

    nexturl = data.xpath("//link[@rel='next']//@href").string()
    if nexturl:
        session.queue(Request(nexturl, use='curl', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').replace(" Review", "").replace(" review", "").split(':')[0].replace('Review of ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].split(".html")[0]
    product.category = data.xpath("//div[@class='single-metainfo']/a[@rel='category tag' and not(regexp:test(., 'review', 'i'))]//text()").string() or 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//meta[@property='article:published_time']//@content").string()
    if date:
        review.date = date.split("T")[0]

    author = data.xpath('//span[contains(@class, "author")]//text()').string(multiple=True)
    if author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('//div[contains(., "To Buy Or Not To Buy")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = h.unescape(conclusion).replace(u'\uFEFF', '').replace('&amp;', '&').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='elementor-row']//p[not(span/a)]//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="elementor-widget-container"]//p[not(em/strong)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='entry-content']//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@class='textwidget']//text()").string(multiple=True)

    if excerpt:
        excerpt = h.unescape(excerpt).replace(u'\uFEFF', '').split("Tags: ")[0].split("Comments")[0].replace('&amp;', '&').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
