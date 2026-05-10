from agent import *
from models.products import *


XTITLE = ['Comparatif ', 'Top des meilleures ', 'Top 10 des meilleures ', 'Top 5 des meilleures ', 'Top 3 des meilleures ', 'Top 20 des meilleures ', 'Top 15 des meilleures ', 'Top 7 des meilleures ', 'Top 8 des meilleures ', 'Top 12 des meilleures ', 'Top 25 des meilleures ', 'Notre sélection des meilleurs ', 'Notre sélection des meilleures ', 'Notre sélection des top ', 'Top des 10 ', 'Top 7 des ', 'Top des meilleurs ']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://technplay.com/tag/test/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//li[@class="g1-collection-item g1-collection-item-1of3"]')
    for rev in revs:
        title = rev.xpath('.//h3[contains(@class, "title")]/a//text()').string(multiple=True)
        cat = rev.xpath('.//a[contains(@class, "entry-category entry-category-item") and not(contains(., "Non classé"))]/text()[normalize-space(.)]').string()
        url = rev.xpath('.//h3[contains(@class, "title")]/a/@href').string()

        if title and url and not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(cat=cat, title=title, url=url))

    next_url = data.xpath('//a/@data-g1-next-page-url').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2]

    name = context['title'].replace('[CRITIQUE]', '').replace('test complet', '').replace('Test du', '').replace('TEST du', '').replace('Test de la', '').replace('Test des', '').replace('Test de', '').replace('[TEST]', '').replace('[TESt]', '').replace('[Test]', '').replace('[NON-TEST]', '').replace('TEST :', '').replace('Test :', '').replace('Test', '').replace('TEST', '').split(':')[0].split(',')[0].replace('J’ai testé ', '').strip()
    product.name = name[0].title() + name[1:]

    product.url = data.xpath('//a[contains(span/text(), "Voir l’offre")]/@href').string()
    if not product.url:
        product.url = context['url']

    category = context['cat']
    if category:
        category = category.replace('Test ', '').strip()
        product.category = category[0].title() + category[1:]
    else:
        product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

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

    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review-final-score"]//span/@style').string()
        if grade_overall:
            grade_overall = grade_overall.replace('width:', '').replace('%', '')
            try:
                grade_overall = round(float(grade_overall) / 20, 1)
                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))
            except:
                pass

    grades = data.xpath('//div[@class="review-item"]/h5/span')
    for grade in grades:
        grade = grade.xpath('text()').string()
        if ' - ' in grade:
            grade_name, grade_val = grade.split(' - ')
            review.grades.append(Grade(name=grade_name.strip(), value=float(grade_val), best=10.0))

    if not grades:
        grades = data.xpath('//div[@class="review-item"]')
        for grade in grades:
            grade_name = grade.xpath('h5/text()').string()
            grade_val = grade.xpath('.//span/@style').string().replace('width:', '').replace('%', '')
            try:
                grade_val = round(float(grade_val) / 20, 1)
                review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))
            except:
                pass

    pros = data.xpath('(//div[not(contains(., "Caractéristiques"))]/div/ul[@class="kt-svg-icon-list"])[last()-1]//span[@class="kt-svg-icon-list-text"]/text()[string-length()>2]').strings()
    if not pros:
        pros = data.xpath('((//h4[contains(., "Points positifs")]|//p[contains(., "Points positifs")])/following-sibling::ul)[1]/li/text()[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "Facebook") or contains(., "Twitter") or contains(., "LinkedIn")) and string-length()>2][normalize-space()]').strings()
    if not pros:
        pros = data.xpath('(//h4[contains(., "Points positifs")]|//p[contains(., "Points positifs")])/following-sibling::p[contains(., "– ")][1]/text()').strings()

    for pro in pros:
        pro = pro.strip(' +-*.:;•,– ')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('(//ul[@class="kt-svg-icon-list" and not(parent::div/parent::div[contains(., "Caractéristiques")])])[last()]//span[@class="kt-svg-icon-list-text"]/text()[string-length()>2]').strings()
    if not cons:
        cons = data.xpath('((//h4[contains(., "Points négatifs")]|//p[contains(., "Points négatifs")])/following-sibling::ul)[1]/li/text()[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "Facebook") or contains(., "Twitter") or contains(., "LinkedIn")) and string-length()>2][normalize-space()]').strings()
    if cons and pros and cons[0] in pros:
        cons = data.xpath('((//h4[contains(., "Points négatifs")]|//p[contains(., "Points négatifs")])/following-sibling::ul)[2]/li//text()[not(contains(., "[one_half]") or contains(., "su_list")) and string-length()>2]').strings()
    if not cons:
        cons = data.xpath('(//h4[contains(., "Points négatifs")]|//p[contains(., "Points positifs")])/following-sibling::p[contains(., "– ")][1]/text()').strings()

    for con in cons:
        con = con.strip(' +-*.:;•,– ')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/following-sibling::p[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "su_box") or contains(., "su_row") or contains(., "[double_paragraph]") or contains(., "[row]"))]//text()[not(starts-with(., ">"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(span//text(), "Verdict")]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/preceding-sibling::p)[not(contains(., "Marque :") or contains(., "Catégorie :") or contains(., "Prix :") or contains(., "Testé avec :") or contains(., "Acheter Misfit Shine :") or contains(., "*Article sponsorisé") or contains(., "[winamaz"))]//text()[not(contains(., "[/slide]") or contains(., "[slideshow]") or contains(., "[slide]") or contains(., "[/slideshow]") or contains(., "»"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/p[not(contains(., "[one_half]") or contains(., "su_list") or contains(., "Marque :") or contains(., "Catégorie :") or contains(., "Prix :") or contains(., "Testé avec :") or contains(., "Acheter Misfit Shine :") or contains(., "*Article sponsorisé") or contains(., "[winamaz"))]//text()[not(contains(., "[/slide]") or contains(., "[slideshow]") or contains(., "[slide]") or contains(., "[/slideshow]") or contains(., "»"))]').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
