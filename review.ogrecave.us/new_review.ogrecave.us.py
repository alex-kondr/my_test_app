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
    session.queue(Request('http://ogrecave.com/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and 'review' in title.lower():
            session.queue(Request(url), process_review_short, dict())

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review_short(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//span[@class="meta-category"]/a[not(contains(., "Review"))]//text()[normalize-space()]').join('/')
    date = data.xpath('//time/@datetime').string()

    revs = data.xpath('//a[contains(@href, "ogrecave.com/reviews/")]/@href[contains(., ".shtml")]')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url), process_review, dict(cat=cats, date=date, url=url))


def process_review(data, context, session):
    strip_namespace(data)

    title = data.xpath('//body/table//td[a/@title="Back to home"]/table/tbody/tr[1]//font/b/text()').string()
    if not title:
        title = data.xpath('//td[@background="/gifs/scrolltile.gif"]/font/b/text()').string()

    product = Product()
    product.ssid = context['url'].split('/')[-1].replace('.shtml', '')
    product.manufacturer = data.xpath('(//text()[contains(., "Published by")]/following-sibling::*)[1]/text()').string()

    product.name = data.xpath('//font/h2/text()').string()
    if not product.name:
        product.name = data.xpath('//td/font[contains(., "by ")]/p[b][1]/b/text()').string()
    if not product.name:
        product.name = title.replace('Reviews - ', '').replace('Reviews: ', '').strip()

    product.url = data.xpath('(//text()[contains(., "Published by")]/following-sibling::*)[1]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = context['cat']
    if not product.category:
        product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = context['date']
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('(//font/h2/preceding-sibling::text()[contains(., "by ")])[1][normalize-space(.)]').string()
    if not author:
        author = data.xpath('//td/font/text()[contains(., "by ")]').string()

    if author:
        author = author.replace('by ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    scores = {'A': 5, 'A-': 4.5, 'B+': 4.5, 'B': 4, 'B-': 3.5, 'C+': 3.5, 'C': 3, 'D': 2, 'E': 1}

    grade_overall = data.xpath('//b[contains(., "Overall Rating:")]/following-sibling::text()[1][contains(., " of ")]').string()
    if not grade_overall:
        grade_overall = data.xpath('//text()[contains(., "Rating:")]').string()

    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].strip()
        if '/' in grade_overall:
            grade_overall = grade_overall.split('/')[0]
            grade_best = 10.0
        else:
            grade_overall = grade_overall.split()[0]
            grade_best = 5.0

        if grade_overall in scores:
            review.grades.append(Grade(type='overall', value=float(scores[grade_overall]), best=5.0))
        elif grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=grade_best))

    grades = data.xpath('//p[contains(.//b, "Ratings")]/b[not(contains(., "Rating"))]')
    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = grade.xpath('following-sibling::text()[1][contains(., " of ")]').string()
        if grade_name and grade_val:
            grade_val = grade_val.split(' of ')[0]

            if grade_overall in scores:
                review.grades.append(Grade(name=grade_name, value=float(scores[grade_overall]), best=5.0))
            elif grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//text()[preceding::p[b][1][contains(., "The Good")] or preceding-sibling::b[contains(., "The Good")]][not(preceding::b[contains(., "Should You Buy") or contains(., "Conclusion")  or contains(., "The Bad")] or contains(., "Should You Buy") or contains(., "Conclusion")  or contains(., "The Bad"))]').string(multiple=True)
    if pros:
        review.add_property(type='pros', value=pros)

    cons = data.xpath('//text()[preceding-sibling::h3[1][contains(., "The Cons")]]').string(multiple=True)
    if not cons:
        cons = data.xpath('//text()[preceding::p[b][1][contains(., "The Bad")] or preceding-sibling::b[contains(., "The Bad")]][not(contains(., "Should You Buy") or contains(., "Conclusion") or preceding-sibling::b[contains(., "Should You Buy") or contains(., "Conclusion")])]').string(multiple=True)

    if cons:
        review.add_property(type='cons', value=cons)

    conclusion = data.xpath('//text()[preceding-sibling::h3[1][contains(., "Conclusions")]]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(b, "Conclusion")]|//p[contains(b, "Conclusion")]/following-sibling::p[1])//text()[not(contains(., "Conclusion"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[contains(b, "Should You Buy")]|//p[contains(b, "Should You Buy")]/following-sibling::p[not(preceding::p[contains(b, "Link")])])//text()[not(contains(., "Should You Buy") or contains(., "Link"))]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//font[contains(., "Published by") or contains(text(), "Rating:")]//text()[not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")])]|//font[contains(., "Published by") or contains(text(), "Rating:")]/p[not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")] or preceding::p[contains(b, "Conclusion") or contains(b, "Should You Buy")])]//text())[not(preceding::*[contains(., "Links:") or contains(., "Should You Buy") or contains(., "Conclusion")] or contains(., "Links:") or contains(., "Should You Buy") or contains(., "Conclusion") or regexp:test(normalize-space(.), "^\$"))][preceding::text()[contains(., "Art by")]][ancestor::p]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//font[contains(., "Published by") or contains(text(), "Rating:")]//text()[not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")])]|//font[contains(., "Published by") or contains(text(), "Rating:")]/p[not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")] or preceding::p[contains(b, "Conclusion") or contains(b, "Should You Buy")])]//text())[not(preceding::*[contains(., "Links:") or contains(., "Should You Buy") or contains(., "Conclusion")] or contains(., "Links:") or contains(., "Should You Buy") or contains(., "Conclusion") or regexp:test(normalize-space(.), "^\$"))][preceding::text()[contains(., "Written by")]][ancestor::p]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//font[contains(., "Published by") or contains(text(), "Rating:")]//text()[not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")])]|//font[contains(., "Published by") or contains(text(), "Rating:")]/p[not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")] or preceding::p[contains(b, "Conclusion") or contains(b, "Should You Buy")])]//text())[not(preceding::*[contains(., "Links:") or contains(., "Should You Buy") or contains(., "Conclusion")] or contains(., "Links:") or contains(., "Should You Buy") or contains(., "Conclusion") or regexp:test(normalize-space(.), "^\$"))][preceding::text()[contains(., "Published by")]][ancestor::p]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//font[contains(., "Published by") or contains(text(), "Rating:")]/p[b or preceding-sibling::p[b]][not(preceding::h3[contains(., "Conclusions") or contains(., "The Cons")] or preceding::p[contains(b, "Conclusion") or contains(b, "Should You Buy") or contains(b, "The Bad") or contains(b, "The Good")] or contains(b, "Conclusion") or contains(b, "Should You Buy") or contains(b, "The Bad") or contains(b, "The Good"))]//text()[not(preceding::*[contains(., "Links:") or contains(., "Should You Buy")] or contains(., "Links:") or contains(., "Should You Buy") or regexp:test(normalize-space(.), "^\$"))][preceding::text()[contains(., "Art by")]][ancestor::p]').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
