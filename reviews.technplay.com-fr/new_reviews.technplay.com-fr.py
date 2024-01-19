from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://technplay.com/tag/test/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[@class="g1-collection-item g1-collection-item-1of3"]')
    for rev in revs:
        title = rev.xpath('.//a[@rel="bookmark"]/text()').string()
        cats = rev.xpath('.//a[contains(@class, "entry-category entry-category-item")]/text()').strings()
        url = rev.xpath('.//a[@rel="bookmark"]/@href').string()
        session.queue(Request(url), process_review, dict(cats=cats, title=title, url=url))

    next_url = data.xpath('//a/@data-g1-next-page-url').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Test du', '').replace('Test de la', '').replace('Test des', '').replace('Test de', '').replace('[TEST]', '').replace('[Test]', '').replace('Test', '').split(':')[0].split(',')[0].strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = '|'.join(context['cats'])

    prod_json = data.xpath('//script[@type="application/ld+json" and contains(., "product")]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        product.sku = prod_json.get('sku')
        product.manufacturer = prod_json.get('brand', {}).get('name')

        ean = prod_json.get('gtin')
        if ean:
            product.add_property(type='id.ean', value=ean)

        mpn = prod_json.get('mpn')
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = context['title']

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/strong/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]/h3/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[@class="review-item"]/h5/span')
    for grade in grades:
        grade = grade.xpath('text()').string()
        if ' - ' in grade:
            grade_name, grade_val = grade.split(' - ')
            review.grades.append(Grade(name=grade_name.strip(), value=float(grade_val), best=10.0))

    pros = data.xpath('(//ul[@class="kt-svg-icon-list"])[last()-1]//span[@class="kt-svg-icon-list-text"]/text()').strings()
    if not pros:
        pros = data.xpath('((//h4[contains(., "Points positifs")]|//p[contains(., "Points positifs")])/following-sibling::ul)[1]/li//text()[not(contains(., "[one_half]") or contains(., "su_list"))]').strings()
    for pro in pros:
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//ul[@class="kt-svg-icon-list"])[last()]//span[@class="kt-svg-icon-list-text"]/text()').strings()
    if not cons:
        cons = data.xpath('((//h4[contains(., "Points négatifs")]|//p[contains(., "Points négatifs")])/following-sibling::ul)[1]/li//text()[not(contains(., "[one_half]") or contains(., "su_list"))]').strings()
    for con in cons:
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@itemprop="articleBody"]/p[1]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Verdict") or contains(., "Conclusion")]/following-sibling::p[not(contains(., "[one_half]") or contains(., "su_list"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "Verdict") or contains(., "Conclusion")]/preceding-sibling::p)[position()>1]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/p[position()>1 and not(contains(., "[one_half]") or contains(., "su_list"))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
