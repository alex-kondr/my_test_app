from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.krinein.com/critiques.php?cat=7', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[contains(@class, "cards")]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    if data.xpath('//span[@class="kr-arthead__type"]/text()[contains(., "Article")]'):
        return

    title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    product = Product()
    product.name = h.unescape(title).split(' - Test')[0].replace('Test Switch - ', '').replace('Le Testament de ', '').replace('Test - ', '').replace('- Test', '').replace(' - TEST', '').replace(' - Preview Steam', '').replace(' - Preview PC', '').replace('Test - ', '').replace(' Test PS4', '').replace(' : le test', '').replace('Thief - Preview : ', '').replace(' - Preview Hands Off', '').replace(' : Preview hands-off', '').replace('Test console - ', '').replace(' - Preview PS Vita', '').replace('Preview - ', '').replace(' - Preview', '').replace('Test de ', '').replace(' -Test', '').replace('Preview ', '').replace('Test ', '').replace(', le test', '').replace(' le test', '').replace(' - Le test pute', '').replace(' Preview', '').replace(' - Greatest hits', '').replace(', la preview', '').replace(' - Bêta test', '').strip(' : ')
    product.ssid = context['url'].split('/')[-2].replace('-preview', '')
    product.category = 'Jeux'
    product.manufacturer = data.xpath('//div[contains(h3, "Développeur")]/ul/li//text()[normalize-space(.)]').string()

    product.url = data.xpath('(//div[contains(h3, "Site officiel")]/ul)[1]/li//a/@href').string()
    if not product.url:
        product.url = context['url']

    platforms = data.xpath('(//div[contains(h3, "Plateforme")]/ul)[1]/li//text()[normalize-space(.)]').join('/')
    if platforms:
        product.category += '|' + platforms.replace(' (Steam)', '').replace(' (PS4)', '').replace(' (PS3)', '').replace(' (Epic)', '').replace('Epic) ', '').replace(' (Steam', '').replace(' (Origin)', '').replace(' (eShop)', '').replace(' (PS3 - PSN)', '').replace(' (XBLA)', '').replace(' (Ps2)', '').replace(' (PS2)', '')

    genres = data.xpath('(//div[contains(h3, "Genre")]/ul)[1]/li//text()[normalize-space(.)]').strings()
    if genres:
        product.category += '|' + '/'.join([genre.replace('/', '\\') for genre in genres])

    review = Review()
    review.type = 'pro'
    review.title = h.unescape(title)
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//div[@class="kr-arthead__byline"]/text()[contains(., "·")]').string()
    if date:
        review.date = date.strip(' ·').split('·')[0].strip()

    author = data.xpath('//div[@class="kr-arthead__byline"]/a/text()').string()
    author_url = data.xpath('//div[@class="kr-arthead__byline"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2].split('-')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="kr-verdict__score"]/span/@aria-label').string()
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].strip().split()[0]
        if grade_overall and grade_overall.isdigit():
            grade_overall = float(grade_overall) / 2
            if grade_overall:
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//p[regexp:test(., ": \d(,\d)?/\d")]//text()[regexp:test(., ": \d(,\d)?/\d") and not(contains(., "Note"))][normalize-space(.)]').strings()
    for grade in grades:
        grade_name = grade.split(':')[0].strip(' .-')
        grade_val = grade.split(':')[-1].split('/')[0].replace(',', '.')
        grade_best = grade.split(':')[-1].split('/')[-1].strip().split()[0]
        if grade_name and grade_val and float(grade_val) > 0 and grade_best.isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)))

    summary = data.xpath('//p[@class="chapo"]//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2[contains(., "Conclusion")]/following-sibling::p)[1]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[normalize-space(.//text())="Conclusion"]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[@class="kr-verdict__txt"])[1]//text()').string(multiple=True)

    if conclusion:
        conclusion = h.unescape(conclusion).replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(contains(., "Tags") or @class or .//img)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[normalize-space(.//text())="Conclusion"]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div/p[not(@class or contains(., "Tags") or .//img or regexp:test(., ": \d\,?\d?/\d") or contains(., "Résumé"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = h.unescape(excerpt).replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
