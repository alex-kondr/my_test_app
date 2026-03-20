from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://jeux-video.krinein.com/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@id="container"]/a')
    for rev in revs:
        title = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = h.unescape(context['title']).split(' - Test')[0].replace('Test Switch - ', '').replace('Le Testament de ', '').replace('Test - ', '').replace('- Test', '').replace(' - TEST', '').replace(' - Preview Steam', '').replace(' - Preview PC', '').replace('Test - ', '').replace(' Test PS4', '').replace(' : le test', '').replace('Thief - Preview : ', '').replace(' - Preview Hands Off', '').replace(' : Preview hands-off', '').replace('Test console - ', '').replace(' - Preview PS Vita', '').replace('Preview - ', '').replace(' - Preview', '').replace('Test de ', '').replace(' -Test', '').replace('Preview ', '').replace('Test ', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Jeux'
    product.manufacturer = data.xpath('(//div[contains(text(), "Développeur")]/following-sibling::ul)[1]/li//text()[normalize-space(.)]').string()

    product.url = data.xpath('(//div[contains(text(), "Site officiel")]/following-sibling::ul)[1]/li//a/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('(//div[contains(text(), "Plateforme")]/following-sibling::ul)[1]/li//text()[normalize-space(.)]').join('/')
    if platforms:
        product.category += '|' + platforms.replace(' (Steam)', '').replace(' (PS4)', '').replace(' (PS3)', '').replace(' (Epic)', '').replace('Epic) ', '').replace(' (Steam', '')

    genres = data.xpath('(//div[contains(text(), "Genre")]/following-sibling::ul)[1]/li//text()[normalize-space(.)]').join('/')
    if genres:
        product.category += '|' + genres

    review = Review()
    review.type = 'pro'
    review.title = h.unescape(context['title'])
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//span[@class="dtreviewed"]/text()').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="reviewer"]/text()').string()
    author_url = data.xpath('//a[span/@class="reviewer"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('u=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating"]/span[@class="value"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//p[@class="chapo"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div/p[not(@class or contains(., "Tags") or .//img)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
