from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


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
    session.queue(Request('https://www.whatcar.com/reviews'), process_catlist, dict())


def process_catlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[contains(@class, "category")]/li//a[@hreflang]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url+'?page=0'), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['name']
    product.category = context['cat']
    product.manufacturer = data.xpath('//nav[@role="navigation"]//a[contains(@href, "/make/")]/text()').string()

    product.ssid = context['url'].split('/')[-1]
    if 'review' in product.ssid:
        product.ssid = product.name.lower().replace(' ', '_').replace(':', '_')

    product.url = data.xpath('//a[contains(., "New car deals") and @data-bi="cta-click"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1//text()').string(multiple=True)
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//div[@class="author-date"]/span[not(contains(., "Updated"))]/text()').string()

    author = data.xpath('//div[contains(@class, "author-name")]/a[contains(@class, "author-link")]/text()').string()
    author_url = data.xpath('//div[contains(@class, "author-name")]/a[contains(@class, "author-link")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "main-title")]//div/@data-rating').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[contains(div/span, "Overview")]/div/@data-rating').string()

    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//h2[contains(@class, "review-chapter-heading") and following-sibling::div[1][contains(@class, "rating-justify-left")]]')
    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = grade.xpath('following-sibling::div[1][contains(@class, "rating-justify-left")]/div/@data-rating').string()
        if grade_name and grade_val and float(grade_val) > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[contains(h3, "Strengths") or contains(h3, "Pros")]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(h3, "Weaknesses") or contains(h3, "Cons")]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "main-title")]/h2//text()').string(multiple=True)
    if summary:
        summary = h.unescape(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "verdict-body")]//text()').string(multiple=True)
    if conclusion:
        conclusion = h.unescape(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "section-content")]/p[not(preceding::h2[regexp:test(., "Buy it if|Don’t buy it if")] or contains(., "For all the latest reviews"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = h.unescape(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
