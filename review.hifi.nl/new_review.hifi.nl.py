from agent import *
from models.products import *
import json


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://hifi.nl/api/solr/content.php?q=&category=Hardware&subCategories=&brands=&years=&from=0&till=10000&order=publishDateDesc&contentType=Recensie&page=1', force_charset="utf-8"), process_frontpage, dict(context, page=1))


def process_frontpage(data, context, session):
    prods_json = json.loads(data.content)
    prods = prods_json['items']
    for prod in prods:
        context['name'] = prod['title'].upper().replace('REVIEW:', '').replace('REVIEW', '').split(':')[0].split(' - ')[0].strip()
        context['title'] = prod['title'].upper()
        context['url'] = 'https://hifi.nl/artikel/' + prod['id'] + '/'
        context['date'] = prod['publishDate'].split('T')[0]
        context['user'] = prod.get('author', '')
        context['category'] = prod['subCategory']
        context['id'] = prod['id']
        if context['url']:
            session.queue(Request(context['url'], use="curl", force_charset="utf-8"), process_product, context)

    if len(prods) >= 10:
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
    review.title = context['title']

    review.authors.append(Person(name=context['user'], ssid=context['id'], url='https://hifi.nl/content?auteur=' + context['user']))

    grade_overall = data.xpath('//*[text()[contains(., "/ 5") or contains(., "Beoordeling")]]/text()').strings()
    if isinstance(grade_overall, list):
        grade_overall_temp = grade_overall[:]
        for item in grade_overall_temp:
            if 'eoordeling' not in item:
                grade_overall.remove(item)
            else:
                break
    if grade_overall:
        grade_overall = ''.join(grade_overall)
        grade_overall = grade_overall.replace(u'\xc2', u' ').replace(':', '').replace('Setbeoordeling set', '').replace('Setbeoordeling', '').replace('Beoordelign', '').replace('Beoordeling', '').replace('beoordeling', '').replace('eoordeling', '').replace(', onvermijdelijk', '').replace(',', '.').replace('/', ' ').replace('uit', ' ').replace('op', ' ').replace('|', '').strip().split()

        try:
            review.grades.append(Grade(value=float(grade_overall[0]), best=5.0, worst=0, name='overall', type='overall'))
        except ValueError:
            pass

    summary = data.xpath('//section[@id="articleBody"]/following-sibling::p/strong/span/text()').string()
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath('//div[@class="conclusieContainer"]/text()').string() or data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[string-length(normalize-space(.)) > 100][1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\t', '').replace('\n', '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath('//section[@id="articleBody"]/*[contains(., "Conclusie")]/preceding-sibling::*[not(strong/span)]//text()').string(multiple=True) or data.xpath('//section[@id="articleBody"]//text()').string(multiple=True)


    pros = data.xpath('//ul[@class="ulPlus"]/li/text()').strings()
    if pros:
        pros = [pro.replace('\n', '').strip() for pro in pros]
        review.properties.append(ReviewProperty(name="PLUSPUNTEN", type="pros", value=pros))

    cons = data.xpath('//ul[@class="ulMin"]/li/text()').strings()
    if cons:
        cons = [con.replace('\n', '').strip() for con in cons]
        review.properties.append(ReviewProperty(name="MINPUNTEN", type="cons", value=cons))


    next_page = data.xpath('//span[@class="pagerItem" and a[@class="orange"]]/following-sibling::*[1]/a/@href').string()
    if next_page:
        review, excerpt = session.do(Request(next_page, force_charset="utf-8"), process_review_next, dict(review=review, excerpt=excerpt))

    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if excerpt or conclusion:
        context['product'].reviews.append(review)


def process_review_next(data, context, session):
    excerpt = context['excerpt']
    review = context['review']
    review.add_property(type='pages', value=dict(title=review.title, url=data.response_url))

    conclusion = data.xpath('//div[@class="conclusieContainer"]/text()|//p[@class="Hoofdtekst" and contains(., "Conclusie")]/text()').string() or data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[string-length(normalize-space(.)) > 100][1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\t', '').replace('\n', '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    new_excerpt = data.xpath('//div[@class="conclusieContainer"]/text()|//p[@class="Hoofdtekst" and contains(., "Conclusie")]/preceding-sibling::*//text()').string(multiple=True) or data.xpath('//section[@id="articleBody"]//text()').string(multiple=True)
    excerpt += ' ' + new_excerpt
    if excerpt and conclusion:
            excerpt = excerpt.replace(conclusion, '')

    next_page = data.xpath('//span[@class="pagerItem" and a[@class="orange"]]/following-sibling::*[1]/a/@href').string()
    if next_page:
        response = session.do(Request(next_page, force_charset="utf-8"), process_review_next, dict(review=review, excerpt=excerpt))
        if response:
            review, excerpt = response

    pros_cons = data.xpath('//div[@class="conclusieContainer"]/text()|//p[@class="Hoofdtekst" and contains(., "Conclusie")]/following-sibling::*//text()').strings()
    if pros_cons:
        for pro_con in pros_cons:
            if pro_con.startswith('+'):
                pro = pro_con.replace('+', '').strip()
                review.properties.append(ReviewProperty(type='pros', value=pro))
            elif pro_con.startswith('-'):
                con = pro_con.replace('-', '').strip()
                review.properties.append(ReviewProperty(type='cons', value=con))

    return review, excerpt
