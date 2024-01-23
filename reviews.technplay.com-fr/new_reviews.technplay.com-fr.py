from agent import *
from models.products import *


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
    product.name = context['title'].replace('[CRITIQUE]', '').replace('test complet', '').replace('Test du', '').replace('TEST du', '').replace('Test de la', '').replace('Test des', '').replace('Test de', '').replace('[TEST]', '').replace('[TESt]', '').replace('[Test]', '').replace('[NON-TEST]', '').replace('TEST :', '').replace('Test :', '').replace('Test', '').replace('TEST', '').split(':')[0].split(',')[0].strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = '|'.join(context['cats'])

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

    pros = data.xpath('(//div[not(contains(., "Caractéristiques"))]/div/ul[@class="kt-svg-icon-list"])[last()-1]//span[@class="kt-svg-icon-list-text"]/text()[string-length()>2]').strings()
    if not pros:
        pros = data.xpath('((//h4[contains(., "Points positifs")]|//p[contains(., "Points positifs")])/following-sibling::ul)[1]/li//text()[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "Facebook") or contains(., "Twitter") or contains(., "LinkedIn")) and string-length()>2][normalize-space()]').strings()
    if not pros:
        pros = data.xpath('(//h4[contains(., "Points positifs")]|//p[contains(., "Points positifs")])/following-sibling::p[contains(., "– ")][1]/text()').strings()
    for pro in pros:
        pro = pro.replace('–', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('(//ul[@class="kt-svg-icon-list"])[last()]//span[@class="kt-svg-icon-list-text"]/text()[string-length()>2]').strings()
    if not cons:
        cons = data.xpath('((//h4[contains(., "Points négatifs")]|//p[contains(., "Points négatifs")])/following-sibling::ul)[1]/li//text()[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "Facebook") or contains(., "Twitter") or contains(., "LinkedIn")) and string-length()>2][normalize-space()]').strings()
    if cons and pros and cons[0] in pros:
        cons = data.xpath('((//h4[contains(., "Points négatifs")]|//p[contains(., "Points négatifs")])/following-sibling::ul)[2]/li//text()[not(contains(., "[one_half]") or contains(., "su_list")) and string-length()>2]').strings()
    if not cons:
        cons = data.xpath('(//h4[contains(., "Points négatifs")]|//p[contains(., "Points positifs")])/following-sibling::p[contains(., "– ")][1]/text()').strings()
    for con in cons:
        con = con.replace('–', '').strip()
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@itemprop="articleBody"]/p[1]//text()').string(multiple=True)
    if summary:
        summary = summary.replace('Test du', '').replace('TEST du', '').replace('Test de la', '').replace('Test des', '').replace('Test de', '').replace('[TEST]', '').replace('[TESt]', '').replace('[Test]', '').replace('[NON-TEST]', '').replace('TEST :', '').replace('Test :', '')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/following-sibling::p[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "su_box") or contains(., "su_row"))]//text()[not(starts-with(., ">"))]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/preceding-sibling::p)[position()>1]//text()[not(contains(., "[/slide]") or contains(., "[slideshow]") or contains(., "[slide]") or contains(., "[/slideshow]") or contains(., "»"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/p[position()>1 and not(contains(., "[one_half]") or contains(., "su_list"))]//text()[not(contains(., "[/slide]") or contains(., "[slideshow]") or contains(., "[slide]") or contains(., "[/slideshow]") or contains(., "»"))]').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
