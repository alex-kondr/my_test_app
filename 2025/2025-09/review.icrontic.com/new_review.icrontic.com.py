from agent import *
from models.products import *


XCAT = ['Community', 'Announcements']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://icrontic.com/', use='curl', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//ul[@class="DataList Discussions"]//li')
    for rev in revs:
        product = Product()
        title = rev.xpath('div/div[@role="heading"]/a/text()').string()
        product.url = rev.xpath('div/div[@role="heading"]/a/@href').string()
        product.ssid = rev.xpath("@id").string().split('_')[-1]
        product.category = rev.xpath('.//span[contains(@class, "Category")]//text()').string(multiple=True)

        if product.category not in XCAT:
            session.queue(Request(product.url, use='curl', max_age=0), process_review, dict(product=product, title=title))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = context['product']

    product.name = context['title'].replace('///SOLD\\\\\\', '').strip()

    review = Review()
    review.type = 'user'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//a[not(@name)]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath("//div[@class='Item-Header DiscussionHeader']/div[@class='AuthorWrap']/span[@class='Author']/a[@class='Username']")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    excerpt = data.xpath("//div[@class='Discussion']/div[@class='Item-BodyWrap']/div[@class='Item-Body']/div[@class='Message userContent']//text()").string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace('![]', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
