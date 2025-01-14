from agent import *
from models.products import *
import json


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://hifi.nl/api/solr/content.php?q=&category=Hardware&subCategories=&brands=&years=&from=0&till=10000&order=publishDateDesc&contentType=Recensie&page=1', force_charset="utf-8"), process_frontpage, dict(context, page=1))


def process_frontpage(data, context, session):
    resp = json.loads(data.content)
    items = resp['items']
    for item in items:
        context['name'] = item['title'].replace('Review: ', '')
        context['url'] = 'https://hifi.nl/artikel/' + str(item['id']) + '/'
        context['date'] = item['publishDate'].split('T')[0]
        context['user'] = item.get('author') or ''
        context['excerpt'] = item['teaser']
        context['category'] = item['subCategory']
        context['id'] = item['id']
        if context['name'] and context['url']:
            session.queue(Request(context['url'], use="curl"), process_product, context)
            #session.queue(Request(context['url'], force_charset="utf8"), process_product, context)

    if len(items) >= 10:
        page = context['page'] + 1
        next_page = 'https://hifi.nl/api/solr/content.php?q=&category=Hardware&subCategories=&brands=&years=&from=0&till=10000&order=publishDateDesc&contentType=Recensie&page=' + str(page)
        session.queue(Request(next_page, force_charset="utf-8"), process_frontpage, dict(context, page=page))


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.category = context['category']
    product.ssid = context['id']
    process_review(data, dict(context, product=product), session)

    if product.reviews:
        session.emit(product)


def process_review(data, context, session):
    review = Review()
    review.ssid = context['id']
    review.url = context['product'].url
    review.type = 'pro'
    review.date = context['date']
    review.title = context['name']
    review.authors.append(Person(name=context['user'], ssid=context['id'], url='https://hifi.nl/content?auteur=' + context['user']))

    p_grade = data.xpath('//span[contains(text(),"Beoordeling")]/text()').strings()
    if p_grade:
        p_grade = p_grade[0].strip().replace(u'\xc2', u' ').replace(':', '').replace('Beoordeling', '').replace(', onvermijdelijk', '').replace(',', '.').replace('/', ' ').replace('uit', ' ').replace('op', ' ')
        grade = p_grade.split()
        review.grades.append(Grade(value=float(grade[0]), best=grade[1], worst=0, name='overall', type='overall'))

    conclusion = data.xpath('//div[@class="conclusieContainer"]/text()').string() or data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[string-length(normalize-space(.)) > 100][1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\t', '').replace('\n', '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    summary = data.xpath('//section[@id="articleBody"]/p[1 or 2]/strong//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath('//section[@id="articleBody"]/p//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if data.xpath('//section[@id="summary"]'):
        p_pros = data.xpath('//ul[@class="ulPlus"]/li/text()').strings()
        p_pros = [f.replace('\n', '').strip() for f in p_pros]
        p_cons = data.xpath('//ul[@class="ulMin"]/li/text()').strings()
        p_cons = [c.replace('\n', '').strip() for c in p_cons]
        if p_pros:
            review.properties.append(ReviewProperty(name="PLUSPUNTEN", type="pros", value=p_pros))
        if p_cons:
            review.properties.append(ReviewProperty(name="MINPUNTEN", type="cons", value=p_cons))

    if excerpt or conclusion:
        context['product'].reviews.append(review)
