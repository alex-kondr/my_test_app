from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://www.psillustrated.com/psillustrated/index_reviews.php/1', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//td[@class="listItem"]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//a[contains(text(), "Next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    title = data.xpath('//td[@class="title"]//text()').string(multiple=True)

    product = Product()
    product.name = title.split('//')[-1].replace(' - Student Review', '').strip()
    product.ssid = context['url'].split('/')[-1]
    product.manufacturer = data.xpath('//div[contains(., "Developer")]/text()[contains(., "Developer")]/following-sibling::b[1]//text()').string()

    product.url = data.xpath('//a[contains(., "Official Homepage")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = 'Games'
    genres = data.xpath('//div[contains(., "Genre")]/text()[contains(., "Genre")]/following-sibling::b//text()').string(multiple=True)
    if genres:
        product.category += '|' + genres.replace(' / ', '/').replace(' (', '/').replace(')', '')

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    author = data.xpath('//a[contains(@href, "reviewer.php")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "reviewer.php")]/@href').string()
    if author and author_url:
        author = author.strip(' +-*.;•–')
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author.strip(' +-*.;•–'), ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.strip(' +-*.;•–')
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(., "Score")]/text()[contains(., "Score")]/following-sibling::b[1]//text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.strip(' %'))
        grade_overall = 100.0 if grade_overall > 100 else grade_overall
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    excerpt = data.xpath('//td[@colspan="2" and not(regexp:test(., "Score:|Genre:|Developer:"))]//div[@class="content"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
