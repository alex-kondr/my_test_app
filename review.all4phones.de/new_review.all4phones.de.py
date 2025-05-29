from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://all4phones.de/forum/handy-testberichte.336/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@data-preview-url]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' im Test: ')[0].replace('Testbericht : ', '').replace('Testbericht: ', '').replace('Testbericht', '').replace('Review: ', '').replace(' im Test', '').replace('Test: ', '').replace('[TEST]', '').replace(' Test', '').replace('Erfahrungsberichte', '').strip()
    product.ssid = context['url'].split('/')[-2].split('.')[-1]
    product.category = 'Technik'

    product.url = data.xpath('//a[@class="link link--external"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//li[@class="u-concealed"]//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//article/@data-author').string()
    if author and 'All4Phones' not in author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[regexp:test(text(), "\d+\.?\d von \d+")]/text()').string()
    if grade_overall:
        grade_overall, grade_best = grade_overall.split(' von ')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(grade_best)))

    pros = data.xpath('//span[span[@style="color: darkgreen"] or b/span[@style="color: darkgreen"] or b[contains(text(), "-")] or starts-with(text(), "-")][not(preceding::*[contains(., "Negativ :")])]//text()')
    for pro in pros:
        pro = pro.string(multiple=True).strip(' +-*.')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[span[contains(text(), "(-)")] or b/span[contains(text(), "(-)")]]/text()[normalize-space(.)]')
    if not cons:
        cons = data.xpath('//*[contains(text(), "Negativ :")]/following::*[starts-with(normalize-space(.), "-")]//text()')

    for con in cons:
        con = con.string(multiple=True).strip(' +-*.')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//span[contains(., "Fazit:")]/following-sibling::text()[normalize-space(.)][not(starts-with(., "-"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//*[contains(., "Fazit:")]/following-sibling::text()[not(starts-with(normalize-space(.), "-"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@class="bbWrapper"])[1]/span/span/*[not(self::b)]//text()[not(preceding::*[regexp:test(., "Fazit:|Positiv :|Negativ :")] or regexp:test(., "Fazit:|Positiv :|Negativ :"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('''(//div[@class="bbWrapper"])[1]/span/span/i/i[not(span[contains(., "Fazit:")])]/text()[not(contains(., "Specs:"))]|//span[@style="font-family: 'Franklin Gothic Medium'"]/span//text()[not(contains(., "IFRAME"))]''').string(multiple=True)

    if excerpt:
        if 'fazit:' in excerpt.lower() and not conclusion:
            conclusion = re.split('Fazit:', excerpt, flags=re.IGNORECASE, maxsplit=1)[-1]
            conclusion = re.split('Positiv :', conclusion, flags=re.IGNORECASE)[0]
            conclusion = re.split('Negativ :', conclusion, flags=re.IGNORECASE)[0]
            review.add_property(type='conclusion', value=conclusion.strip())

        excerpt = re.split('Fazit:', excerpt, flags=re.IGNORECASE)[0]
        excerpt = re.split('Positiv :', excerpt, flags=re.IGNORECASE)[0]
        excerpt = re.split('Negativ :', excerpt, flags=re.IGNORECASE)[0].strip()

        if len(excerpt) > 2:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
