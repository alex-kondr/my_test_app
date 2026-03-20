from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
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
        product.category += '|' + platforms.replace(' (Steam)', '').replace(' (PS4)', '').replace(' (PS3)', '').replace(' (Epic)', '').replace('Epic) ', '').replace(' (Steam', '').replace(' (Origin)', '').replace(' (eShop)', '').replace(' (PS3 - PSN)', '').replace(' (XBLA)', '')

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

    grades = data.xpath('//p[regexp:test(., ": \d\,?\d?/\d")]//text()[regexp:test(., ": \d\,?\d?/\d")][normalize-space(.)]').strings()
    for grade in grades:
        grade_name = grade.split(':')[0].strip(' .-')
        grade_val = grade.split(':')[-1].split('/')[0].replace(',', '.')
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    summary = data.xpath('//p[@class="chapo"]//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(.//img or regexp:test(., ": \d\,?\d?/\d") or contains(., "Résumé"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = h.unescape(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(contains(., "Tags") or @class or .//img)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[not(@class or contains(., "Tags") or .//img or regexp:test(., ": \d\,?\d?/\d") or contains(., "Résumé"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = h.unescape(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
