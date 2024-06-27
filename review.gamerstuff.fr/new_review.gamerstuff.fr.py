from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://gamerstuff.fr/category/tests/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="p-featured"]//a')
    for rev in revs:
        title = rev.xpath('@title').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' – ')[0].replace('Test ', '').split(' : ')[0].strip()
    product.ssid = context['url'].split('/')[-2].replace('test-', '')
    product.category = 'Technologie'

    product.url = data.xpath('//a[@class="lnk-review-cdiscount"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[@class="lnk-review-amazon"]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[@class="review-btn is-btn"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="meta-el meta-author"]/a/text()').string()
    author_url = data.xpath('//span[@class="meta-el meta-author"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="meta-score h4"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review-final-score"]//text()').string()
        if grade_overall:
            grade_overall = grade_overall.strip(' %')
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="review-label"]')
    for grade in grades:
        grade_name = grade.xpath('.//span[@class="review-label-info h4"]/text()').string()
        grade_val = grade.xpath('.//span[@class="rating-info is-meta"]/text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    if not grades:
        grades = data.xpath('//div[@class="review-item"]')
        for grade in grades:
            grade_name, grade_val = grade.xpath('.//h5//text()').string(multiple=True).split(' - ')
            grade_name = grade_name.strip()
            grade_val = grade_val.strip(' %')
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//span[i[@class="rbi rbi-like"]]/following-sibling::span')
    if not pros:
        pros = data.xpath('//div[@class="review-plus"]')
    if not pros:
        pros = data.xpath('(//div[@class="review-col-more" and contains(., "Les plus")]//ul)[1]//li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro and len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[i[@class="rbi rbi-dislike"]]/following-sibling::span')
    if not cons:
        cons = data.xpath('//div[@class="review-moins"]')
    if not cons:
        cons = data.xpath('//div[@class="review-col-more" and contains(., "Les moins") and not(contains(., "Les plus"))]//li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con and len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="summary-content"]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(@id, "conclusion")]/following-sibling::p[not(contains(., "Les plus") or contains(., "Les moins"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//body//p[not(contains(@class, "comment") or contains(., "Caractéristiques générales") or contains(., "Poids et dimensions") or contains(., "Données techniques") or contains(., "Matériaux utilisés") or contains(., "Les plus") or contains(., "Les moins") or contains(., "•") or contains(., "A l’intérieur de cette même boite, on retrouve"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        comments = data.xpath('//div[@class="comment-content"]')
        for comment in comments:
            excerpt = excerpt.replace(comment.xpath('.//text()').string(multiple=True), '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
