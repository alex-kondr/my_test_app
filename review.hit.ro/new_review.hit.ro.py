from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.hit.ro/gadgeturi/review.html'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2/a')
    for rev in revs:
        title = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        if title and url:
            session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(., "chevron_right")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').split('Review:')[0].split('- Preview')[0].split('review:')[0].split(' Review - ')[0].split(' review - ')[0].split('Review monitor')[-1].split('- Review')[0].split(' - review Hit.ro')[0].split('- REVIEW')[0].split('Review HIT.ro -')[-1].split('Review HIT:')[-1].split('HIT Shop:')[-1].replace('Review-uri la', '').replace('Mini Review', '').split(': prezentare')[0].split('Review HIT.ro:')[-1].split('Test ')[-1].split('Tips:')[-1].split('Tips!')[-1].replace('Review HIT.ro', '').replace('Review', '').strip()
    product.url = context['url']
    product.category = 'Gadgeturi'
    product.ssid = product.url.split('--')[-1].replace('.html', '')

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.type = 'pro'
    review.ssid = product.ssid

    date = data.xpath('//div[@class="card-content"]/span[contains(., "calendar")]/text()').string()
    if date:
        review.date = date.split(',')[0]

    author = data.xpath('//span[@itemprop="author"]//span[@itemprop="name"]/text()[not(contains(., "hit.ro"))]').string()
    author_url = data.xpath('//span[@itemprop="author"]/a/@href').string()
    if author and author_url:
        author = author.split(':')[-1].strip(' ]')
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        author = author.split(':')[-1].strip(' ]')
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="card-content"]//text()[regexp:test(., "finala:", "i")]').string()
    if grade_overall:
        grade_overall = float(grade_overall.split(':')[-1].replace(',', '.').strip())
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    pros = data.xpath('//strong[contains(., "aspecte pozitive putem")]/following-sibling::text()[preceding-sibling::strong[1][contains(., "aspecte pozitive putem")] and starts-with(., "-")]')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//strong[contains(., "aspectele mai putin")]/following-sibling::text()[preceding-sibling::strong[1][contains(., "aspectele mai putin")] and starts-with(., "-")]')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//strong[regexp:test(., "Concluzi", "i")]/following-sibling::text()|(//strong[regexp:test(., "Concluzi", "i")]/following-sibling::a|//strong[regexp:test(., "Concluzi", "i")]/following-sibling::p|//strong[regexp:test(., "Concluzi", "i")]/following-sibling::strong)//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@itemprop="articleBody"]/text()|(//div[@itemprop="articleBody"]/strong|//div[@itemprop="articleBody"]/a|//div[@itemprop="articleBody"]/p)//text())[not(contains(., "(cllic pe imagin") or contains(., "(clic pe imagin") or regexp:test(., "Specificatii|concluzi", "i") or preceding-sibling::text()[regexp:test(., "SPECIFICATII|Concluzi", "i")])]').string(multiple=True)
    if excerpt:
        grades = re.findall(r'(Intro/Poveste|Grafica|Gameplay|Sunete/Muzica|Realism|A\.I\.|Multiplayer|Rejucabilitate) \d{1,2},?\d?', excerpt)
        for grade in grades:
            grade_name, grade_val = grade.split()
            grade_val = grade_val.replace(',', '.')
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

        excerpt = excerpt.split('Criteriu Nota Plusuri')[0]
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
