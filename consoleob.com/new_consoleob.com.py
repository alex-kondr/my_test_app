from agent import *
from models.products import *


XCAT = ['E3 2019', 'E3 2018', 'E3 2017', 'Features', 'Novels', 'Films']


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.consoleob.com/'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//ul[@id="subnav"]/li/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if url and name and name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="front-post"]/b/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace(' Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']
    product.manufacturer = data.xpath('//p[contains(., "Developer:")]/strong[not(contains(., "Publisher:"))]/text()').string()

    genre = data.xpath('//strong[contains(span, "Genre:")]/text()').string()
    if genre:
        product.category += '|' + genre

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//span[@class="time"]/text()').string()

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('(//div[@class="postarea"]/p[strong])[last()]/strong/text()[regexp:test(., "^\d{1,2}/\d{1,2}$")]').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    excerpt = data.xpath('//div[@class="postarea"]/p[not(regexp:test(strong, "Publisher:|Genre:|Age Rating:|^\d+/\d+$"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
