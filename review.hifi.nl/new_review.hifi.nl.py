from agent import *
from models.products import *
import json


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://hifi.nl/api/solr/content.php?q=&category=Hardware&subCategories=&brands=&years=&from=0&till=10000&order=publishDateDesc&contentType=Recensie&page=1', force_charset="utf-8"), process_revlist, dict(context, page=1))


def process_revlist(data, context, session):
    prods_json = json.loads(data.content)
    prods = prods_json['items']
    for prod in prods:
        context['title'] = prod['title']
        context['id'] = prod['id']
        context['url'] = 'https://hifi.nl/artikel/' + context['id'] + '/'
        context['date'] = prod['publishDate'].split('T')[0]
        context['user'] = prod.get('author')
        context['category'] = prod['subCategory']
        if context['url']:
            session.queue(Request(context['url'], use="curl", force_charset="utf-8"), process_product, context)

    if len(prods) >= 10:
        page = context['page'] + 1
        next_page = 'https://hifi.nl/api/solr/content.php?q=&category=Hardware&subCategories=&brands=&years=&from=0&till=10000&order=publishDateDesc&contentType=Recensie&page=' + str(page)
        session.queue(Request(next_page, force_charset="utf-8"), process_revlist, dict(context, page=page))


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').replace('Review', '').split(':')[0].split(' - ')[0].strip()
    product.url = context['url']
    product.category = context['category']
    product.ssid = context['id']
    product.manufacturer = data.xpath('//span[@class="b_black large"]/a/text()').string()

    review = Review()
    review.ssid = context['id']
    review.url = product.url
    review.type = 'pro'
    review.date = context['date']
    review.title = context['title']

    if context['user']:
        review.authors.append(Person(name=context['user'], ssid=context['user'], url='https://hifi.nl/content?auteur=' + context['user'].replace(' ', '%20')))

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
            review.grades.append(Grade(value=float(grade_overall[0]), best=5.0, worst=0, type='overall'))
        except ValueError:
            pass

    summary = data.xpath('//section[@id="articleBody"]/following-sibling::p/strong/span/text()').string()
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath('//div[@class="conclusieContainer"]/text()').string()
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[string-length(normalize-space(.)) > 100][1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\t', '').replace('\n', '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    context['excerpt'] = data.xpath('//section[@id="articleBody"]/*[contains(., "Conclusie")]/preceding-sibling::*[not(strong/span)]//text()').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//section[@id="articleBody"]/p//text()').string(multiple=True)
    if not context['excerpt']:
            context['excerpt'] = data.xpath('//section[@id="articleBody"]//*[contains(., "Conclusie")]/preceding-sibling::*//text()').string(multiple=True)

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
        page = 1
        review.add_property(type='pages', value=dict(title=review.title + ' - page ' + str(page), url=data.response_url))
        session.do(Request(next_page, force_charset="utf-8"), process_review_next, dict(context, product=product, review=review, page=page + 1))

    else:
        context['product'] = product
        context['review'] = review
        context['page'] = 1
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    product = context['product']
    review = context['review']
    excerpt = context['excerpt']

    page = context['page']
    if page > 1:
        review.add_property(type='pages', value=dict(title=review.title + ' - page ' + str(page), url=data.response_url))

        new_excerpt = data.xpath('//div[@class="conclusieContainer"]/text()|//p[@class="Hoofdtekst" and contains(., "Conclusie")]/preceding-sibling::*//text()').string(multiple=True)
        if not new_excerpt:
            new_excerpt = data.xpath('//section[@id="articleBody"]//*[contains(., "Conclusie")]/preceding-sibling::*//text()').string(multiple=True)
        if not new_excerpt:
            new_excerpt = data.xpath('//section[@id="articleBody"]/p//text()').string(multiple=True)
        if not new_excerpt:
            new_excerpt = data.xpath('//section[@id="articleBody"]//p//text()').string(multiple=True)
        if new_excerpt:
            excerpt += ' ' + new_excerpt

    conclusion = data.xpath('//div[@class="conclusieContainer"]/text()|//p[@class="Hoofdtekst" and contains(., "Conclusie")]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[string-length(normalize-space(.)) > 100][1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\t', '').replace('\n', '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    if excerpt and conclusion:
            excerpt = excerpt.replace(conclusion, '')

    next_page = data.xpath('//span[@class="pagerItem" and a[@class="orange"]]/following-sibling::*[1]/a/@href').string()

    pros_cons = data.xpath('//div[@class="conclusieContainer"]/text()|//p[@class="Hoofdtekst" and contains(., "Conclusie")]/following-sibling::*//text()').strings()
    if pros_cons:
        pros = [pro.replace('+', '').strip() for pro in pros_cons if pro.startswith('+')]
        if pros:
            review.properties.append(ReviewProperty(type='pros', value=pros))

        cons = [con.replace('-', '').strip() for con in pros_cons if con.startswith('-')]
        if cons:
            review.properties.append(ReviewProperty(type='cons', value=cons))
    else:
        pros = data.xpath('//p[@class="p1"]/span[normalize-space(text()) and not(contains(text(), "+"))]/text()').strings()
        if pros:
            review.properties.append(ReviewProperty(type='pros', value=pros))

        cons = data.xpath('//p[@class="p2"]/span[normalize-space(text()) and not(contains(text(), "-"))]/text()').strings()
        if cons:
            review.properties.append(ReviewProperty(type='cons', value=cons))

    if next_page:
        session.do(Request(next_page, force_charset="utf-8"), process_review_next, dict(product=product, review=review, excerpt=excerpt, page=page + 1))

    elif excerpt or conclusion:
        if excerpt:
            review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)

        session.emit(product)
