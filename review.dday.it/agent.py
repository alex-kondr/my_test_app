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
    session.queue(Request('https://www.dday.it/prove', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[@class="preview"]/section')
    for rev in revs:
        title = rev.xpath('a/h2/text()').string()
        cat = rev.xpath('.//span[@class="category"]/a/text()').string()
        url = rev.xpath('a[h2]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, cat=cat, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(', la recensione')[0].split(', recensione')[0].split(' in prova: ')[0].strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-recensione', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@class="date"]/text()').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//h2[not(@class)]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//section[@class="article-body"]/section/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//section[@class="article-body"]/p//text()').string(multiple=True)

    rev_info = data.xpath('//script[contains(., "product_id")]/text()').string()
    if rev_info:
        rev_id = rev_info.split("?product_id=")[-1].split("'")[0]
        next_url = 'https://www.dday.it/review_snippet?product_id={}'.format(rev_id)
        session.do(Request(next_url, use='curl', force_charset='utf-8'), process_review_next, dict(product=product, review=review, excerpt=excerpt))

    elif excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_next(data, context, session):
    strip_namespace(data)

    review = context['review']

    grade_overall = data.xpath('//li[contains(@class, "total")]/div[@class="score"]//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//li[not(contains(@class, "total")) and div[@class="score"]]')
    for grade in grades:
        grade_name = grade.xpath('label/text()').string()
        grade_val = grade.xpath('div/text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[h2[contains(., "Cosa ci piace")]]/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h2[contains(., "Cosa non ci piace")]]/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//section[@class="product-summary"]/div[h3]/p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
