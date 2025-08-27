from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('https://top-mob.com/?s=%D0%9E%D0%91%D0%97%D0%9E%D0%A0', max_age=0), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[contains(@class, "post-")]')
    for rev in revs:
        title = rev.xpath(".//h2[@class='entry-title']//text()").string()
        ssid = rev.xpath('@id').string()
        grade_overall = rev.xpath('.//p[contains(., "Оценка:")]/b/text()').string()
        url = rev.xpath(".//h2[@class='entry-title']/a/@href").string()

        if title and url:
            session.queue(Request(url, max_age=0), process_review, dict(title=title, ssid=ssid, grade_overall=grade_overall, url=url))
            
            
    print('revs=', len(revs))

    if len(revs) == 10:
        next_page = context.get('page', 1) + 1
        next_url = 'https://top-mob.com/page/{}/?s=%D0%9E%D0%91%D0%97%D0%9E%D0%A0'.format(next_page)
        session.queue(Request(next_url, max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' ОБЗОР: ')[0].replace(' ОБЗОР', '').strip()
    product.ssid = context['ssid'].replace('post-', '')
    product.category = data.xpath("//span[@class='cat-links']/a//text()").string()
    product.url = context['url']

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    date = data.xpath("//time[@class='entry-date published']/@datetime").string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//span[@class='author vcard']//text()").string(multiple=True)
    author_url = data.xpath("//span[@class='author vcard']/a/@href").string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    if context['grade_overall']:
        grade_overall = context['grade_overall'].split(' из ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//h2[contains(., "Преимущества")]/following-sibling::*)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h2[contains(., "Недостатки")]/following-sibling::*)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "Стоит ли покупать|Итог|Вывод|Рекомендац", "i")]/following-sibling::p[not(@class or small or regexp:test(., "Не забудьте заглянуть"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Стоит ли покупать|Итог|Вывод|Рекомендац", "i")]/preceding-sibling::p[not(@class or @style or small or regexp:test(., "Не забудьте заглянуть"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]//p[not(@class or @style or small or regexp:test(., "Не забудьте заглянуть"))]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
