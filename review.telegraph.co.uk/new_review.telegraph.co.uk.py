from agent import *
from models.products import *


XTITLE = ['the best']


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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.telegraph.co.uk/recommended/tech/', use='curl', force_charset='utf-8'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//div[@data-test="article-list-heading-link-wrapper" and a[contains(@href, "/tech/")]]')
    for cat in cats:
        name = cat.xpath('.//h2/text()').string(multiple=True)
        url = cat.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@data-track-wrapper, "article-list")]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()

        if url and title and not any(xtitle in title.lower() for xtitle in XTITLE) and 'review' in url:
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']

    product.name = data.xpath('//h2[@class="product-review__name"]/text()').string()
    if not product.name:
        product.name = context['title']

    product.url = data.xpath('//a[@name="buy"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@data-test="author-name"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//svg[@title="filled star"]) + count(//svg[@title="half star"]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//p[regexp:test(normalize-space(.), "^Score: \d/\d$")]')
    for grade in grades:
        grade_name = grade.xpath('(preceding-sibling::*)[last()][self::h2]//text()').string(multiple=True)
        grade_val = grade.xpath('text()').string(multiple=True)
        if grade_name and grade_val:
            grade_val = grade_val.split('/')[0]
            if grade_val and grade_val.isdigit() and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[contains(@class, "review__pros")]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–►…')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "review__cons")]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–►…')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@data-test="standfirst"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Should you buy|Verdict|Conclusion", "i")]/following-sibling::p[not(regexp:test(strong/text(), "Yes, if:|No, if:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@data-test="article-body-text"]/p[not(preceding::h2[regexp:test(., "Should you buy|Verdict|Conclusion", "i")] or regexp:test(normalize-space(.), "^Score: \d/\d$"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
