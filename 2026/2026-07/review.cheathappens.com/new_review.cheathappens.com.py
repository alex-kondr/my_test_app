from agent import *
from models.products import *
import time
import random


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
    session.queue(Request('https://www.cheathappens.com/reviews_index.asp?letter=ALL&pl=0'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(2, 5))

    revs = data.xpath('//li[contains(@class, "list-group-item")]/div')
    for rev in revs:
        title = rev.xpath('.//a/text()').string()
        date = rev.xpath('div[last()]/text()').string()
        url = rev.xpath('.//a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, date=date, url=url))

# load all revs


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    time.sleep(random.uniform(2, 5))

    product = Product()
    product.name = context['title'].replace(' Review ', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('_review', '').replace('.asp', '')
    product.category = 'Games'
    product.manufacturer = data.xpath('(//span[contains(., "Developer:")]/following-sibling::strong)[1]/text()').string()

    platform = data.xpath('//div[@class="revheadPlatform"]/text()').string()
    if not platform:
        platform = data.xpath('(//span[contains(., "Reviewed on:")]/following-sibling::strong)[1]/text()').string()

    if platform:
        product.category += '|' + platform

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['date']

    author = data.xpath('//div[@class="reviewerText"]/span/text()').string()
    if not author:
        author = data.xpath('//td[strong[contains(., "Review by:")]]/text()').string()
    if not author:
        author = data.xpath('//span[@class="text11" and starts-with(normalize-space(.), "by")]/text()').string()

    if author:
        if author.startswith('by '):
            author = author.replace('by ', '')

        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="scoreOverallNum"]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//tr[td/img[contains(@src, "/reviews/rate")] and contains(., "Overall")]/td/img/@alt').string()
    if not grade_overall:
        grade_overall = data.xpath('//tr[td[contains(@class, "text_orange")] and contains(., "Overall")]/td[contains(@class, "text_orange")]/text()').string()

    if grade_overall:
        grade_overall = grade_overall.split('/')[0].strip()
        if grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[regexp:test(@class, "rating\w+S$") and not(contains(@class, "Overall"))]')
    for grade in grades:
        grade_name = grade.xpath('(preceding-sibling::div)[last()]/text()').string()
        grade_val = grade.xpath('text()').string()
        if grade_name and grade_val and float(grade_val) > 0:
            grade_name = grade_name.strip(' :')
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    if not grades:
        grades = data.xpath('//tr[td[contains(@class, "text_orange")] and not(contains(., "Overall"))]')
        for grade in grades:
            grade_name = grade.xpath('td[not(contains(@class, "text_orange"))]//text()').string(multiple=True)
            grade_val = grade.xpath('td[contains(@class, "text_orange")]/text()').string()
            if grade_name and grade_val:
                grade_name = grade_name.strip(' :')
                grade_val = grade_val.split('/')[0]
                if grade_val[0].isdigit() and float(grade_val) > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    if not grades:
        grades = data.xpath('//td[span[@class="scoreOverallSmall"]]')
        for grade in grades:
            grade_name = grade.xpath('.//text()').string(multiple=True)
            grade_val = grade.xpath('(following-sibling::td)[1]//text()').string(multiple=True)
            if grade_name and grade_val and float(grade_val) > 0:
                grade_name = grade_name.strip(' :')
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    if not grades:
        grades = data.xpath('//tr[td/img[contains(@src, "/reviews/rate")] and not(contains(., "Overall"))]')
        for grade in grades:
            grade_name = grade.xpath('td[1]//text()').string(multiple=True)
            grade_val = grade.xpath('td/img/@alt').string()
            if grade_name and grade_val and grade_val.isdigit() and float(grade_val) > 0:
                grade_name = grade_name.strip(' :')
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    conclusion = data.xpath('//p[contains(span, "Conclusion")]//text()[not(contains(., "Conclusion"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//tr[contains(., "Overall")]/following-sibling::tr)[1]/td//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//span[@class="blacktext12"]/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="revPara"]/p[not(contains(span, "Conclusion"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//td[@class="opentext"]/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//td/img[contains(@src, "/reviews/rate")])[last()]/following::tr/td[p][not(preceding::span[contains(., "COMMENTS")] or contains(@class, "factorbox") or .//span[@class="title2"])]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
