from agent import *
from models.products import *
import re


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.vooks.net/category/nintendo-switch/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Switch'))
    session.queue(Request('https://www.vooks.net/category/switch-2/', use='curl', force_charset='utf-8'), process_revlist, dict(cat='Switch 2'))


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="col-md-6 loop-column"]//div[regexp:test(@class, "category-\d+")]')
    for rev in revs:
        title = rev.xpath('.//h2[@class="article-title"]//text()').string(multiple=True)
        url = rev.xpath('a/@href').string()

        if title and 'review' in title.lower():
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = re.sub(r'\(.+\)', '', context['title']).split(' – ')[0].replace(' accessories reviewed', '').replace(' Review', '').replace(' Review', '').replace(' reviewed', '').replace('Preview: ', '').replace(' Preview', '').replace(' review', '').replace('Review: ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//span[@class="author"]/a|//a[@itemprop="author"])//text()').string()
    author_url = data.xpath('(//span[@class="author"]/a|//a[@itemprop="author"])/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[contains(@class, "rating editor_rating")]//span[contains(@class, "star-full")]) + count(//div[contains(@class, "rating editor_rating")]//span[contains(@class, "star-half")]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grade_user = data.xpath('count(//div[contains(@class, "total-rating-wrapper") and contains(., "User Rating")]//span[contains(@class, "star-full")]) + count(//div[contains(@class, "total-rating-wrapper") and contains(., "User Rating")]//span[contains(@class, "star-half")]) div 2')
    if grade_user:
        review.grades.append(Grade(name='User Rating', value=float(grade_user), best=5.0))

    grades = data.xpath('//div[@data-reaction]')
    for grade in grades:
        grade_name = grade.xpath('div[@class="reaction-text"]/text()').string()
        grade_val = grade.xpath('div[contains(@class, "percentage")]/text()').string().strip(' %')
        if grade_overall and float(grade_val.strip(' %')) > 0:
            grade_val = float(grade_val.strip(' %'))
            review.grades.append(Grade(name=grade_name, value=grade_val, best=100.0))

    pros = data.xpath('//div[@class="procon pro"]/p/text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="procon con"]/p/text()')
    for con in cons:
        con = con.string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[div[contains(text(), "Final Thoughts")]]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@id, "content")]/p[not(@class or contains(., "Rating")) and preceding-sibling::hr]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@id, "content")]/p[not(@class or contains(., "Rating") or preceding-sibling::hr)]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
