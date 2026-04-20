from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.doblu.com/category/blu-ray-reviews/'), process_category, dict(cat='Films|Blu-ray'))


def process_category(data, context, session):
    cats = data.xpath('//div[contains(div/text(), "Blu-ray")]/div/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=context['cat']+'|'+name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="doblu-review-card"]')
    for rev in revs:
        title = rev.xpath('.//div[contains(@class, "card__title")]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.ssid = data.xpath('//body[contains(@class, "postid-")]/@class').string().split('postid-')[-1].split()[0]
    product.category = context['cat']

    name = data.xpath('//h5[@class="review-title"]/text()').string()
    if not name:
        name = context['title']

    product.name = name.split(' Blu-ray')[0].split(' Review')[0].split(' review')[0]

    product.url = data.xpath('//a[@class="doblu-amazon__btn"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time" or @property="og:updated_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "article-hero__byline")]/span[1]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "score-panel__num")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//span[@class="review-total-box"]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('count(//p[strong[@class="rating"][contains(., "Movie")]]//img[@alt="★"])')
    if not grade_overall:
        grade_overall = data.xpath('//p[strong[@class="rating"][contains(., "Movie")]]//img/@title').string()
    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., "rating=") and contains(., "label=Movie")]//text()').string(multiple=True)

    if grade_overall:
        grade_overall = str(grade_overall).split('rating=')[-1].split('/')[0]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//ul[@class="review-list"]/li')
    if not grades:
        grades = data.xpath('//p[strong[@class="rating"] and not(contains(., "Movie"))]')
    if not grades:
        grades = data.xpath('//p[contains(., "rating=") and not(contains(., "label=Movie"))]')

    for grade in grades:
        grade_name = grade.xpath('span/text()').string()
        if not grade_name:
            grade_name = grade.xpath('strong/text()').string()
        if not grade_name:
            grade_name = grade.xpath('.//text()').string(multiple=True)

        grade_value = grade.xpath('.//div[@class="review-result"]/@style').string()
        if not grade_value:
            grade_value = grade.xpath('count(.//img[@alt="★"])')
        if not grade_value:
            grade_value = grade.xpath('following-sibling::div[1]/img[@alt="★"]/@title').string()
        if not grade_value:
            grade_value = grade.xpath('.//img/@title').string()
        if not grade_value:
            grade_value = grade.xpath('.//text()').string(multiple=True)

        if grade_name and grade_value:
            grade_name = grade_name.split('label=')[-1].split(']')[0]
            grade_value = str(grade_value).split('rating=')[-1].split('/')[0].split(':', 1)[-1].split('%')[0].split()[0]

            if grade_value.split('.')[0].isdigit():
                if grade_value and float(grade_value) > 5:
                    grade_value = float(grade_value) / 20

                if product.name.lower().strip() in grade_name.lower().strip():
                    review.grades.append(Grade(type='overall', value=float(grade_value), best=5.0))
                else:
                    review.grades.append(Grade(name=grade_name, value=float(grade_value), best=5.0))

    conclusion = data.xpath('//div[@class="review-desc"]/p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="doblu-prose"]/p[not(@class or contains(., "luchshie vechnie ssilki") or contains(., "Full disclosure"))][not(.//a[contains(., "subscription-exclusive")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
