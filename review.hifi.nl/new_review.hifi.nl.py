from agent import *
from models.products import *
import json


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
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
        if context['url']:
            session.queue(Request(context['url'], use="curl", force_charset="utf-8"), process_product, context)

    if len(items) >= 10:
        page = context['page'] + 1
        next_page = 'https://hifi.nl/api/solr/content.php?q=&category=Hardware&subCategories=&brands=&years=&from=0&till=10000&order=publishDateDesc&contentType=Recensie&page=' + str(page)
        session.queue(Request(next_page, force_charset="utf-8"), process_frontpage, dict(context, page=page))


def process_product(data, context, session):
    product = Product()
    
    name = data.xpath('//p[@class="Info"]/strong/text()').string() or data.xpath('//p/strong/text()').string()
    if name:
        product.name = name
    else:
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
    
    title = data.xpath('//meta[@property="og:title"]/@content').string()
    if title:
        review.title = title.replace('Review', '').strip()
    
    review.authors.append(Person(name=context['user'], ssid=context['id'], url='https://hifi.nl/content?auteur=' + context['user']))

    p_grade = data.xpath('//*[text()[contains(., "/ 5") or contains(., "Beoordeling")]]/text()').strings()
    if isinstance(p_grade, list):
        p_grade_temp = p_grade[:]
        for item in p_grade_temp:
            if 'eoordeling' not in item:
                p_grade.remove(item)
            else:
                break
    if p_grade:            
        p_grade = ''.join(p_grade)
        grade = p_grade.replace(u'\xc2', u' ').replace(':', '').replace('Setbeoordeling set', '').replace('Setbeoordeling', '').replace('Beoordelign', '').replace('Beoordeling', '').replace('beoordeling', '').replace('eoordeling', '').replace(', onvermijdelijk', '').replace(',', '.').replace('/', ' ').replace('uit', ' ').replace('op', ' ').replace('|', '').strip().split()

        try:
            review.grades.append(Grade(value=float(grade[0]), best=5.0, worst=0, name='overall', type='overall'))
        except ValueError as error:
            print('ValueError=', error)

    conclusion = data.xpath('//div[@class="conclusieContainer"]/text()').string() or data.xpath('//h2[contains(., "Conclusie")]/following-sibling::p[string-length(normalize-space(.)) > 100][1]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace('\t', '').replace('\n', '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
        
    excerpt = data.xpath('//section[@id="articleBody"]//h2[contains(., "Conclusie")]/preceding-sibling::*//text()').string(multiple=True) or data.xpath('//section[@id="articleBody"]//text()').string(multiple=True)

    if data.xpath('//section[@id="summary"]'):
        p_pros = data.xpath('//ul[@class="ulPlus"]/li/text()').strings()
        p_pros = [f.replace('\n', '').strip() for f in p_pros]
        p_cons = data.xpath('//ul[@class="ulMin"]/li/text()').strings()
        p_cons = [c.replace('\n', '').strip() for c in p_cons]
        if p_pros:
            review.properties.append(ReviewProperty(name="PLUSPUNTEN", type="pros", value=p_pros))
        if p_cons:
            review.properties.append(ReviewProperty(name="MINPUNTEN", type="cons", value=p_cons))
            
    
    next_page = data.xpath('//span[@class="pagerItem"]/a[@class="" and contains(@href, "pagina")]/@href').string()
    page = data.xpath('//span[@class="pagerItem"]/a[@class="" and contains(@href, "pagina")]/text()').string()
    count_pages = data.xpath('count(//span[@class="pagerItem"])')
    if next_page and int(page) <= int(count_pages):
        review, excerpt = session.do(Request(next_page, force_charset="utf-8"), process_review_next, dict(review=review, excerpt=excerpt, page=2))

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

    page = context['page'] + 1
    next_page = data.response_url.replace('pagina' + str(context['page']), 'pagina' + str(page)).replace(data.response_url.split('/')[-1], '')
    next_pages = data.xpath('//span[@class="pagerItem"]/a[@class="" and contains(@href, "pagina")]/@href').strings()
    for n_page in next_pages:
        if ('pagina' + str(page)) in n_page:
            response = session.do(Request(next_page, force_charset="utf-8"), process_review_next, dict(review=review, excerpt=excerpt, page=page))
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
