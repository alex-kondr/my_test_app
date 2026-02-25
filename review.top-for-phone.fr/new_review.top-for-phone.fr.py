from agent import *
from models.products import *
import simplejson


XTITLE = ['Unboxing de', ' vs ']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://www.top-for-phone.fr/category/tests', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if not any(xtitle in title for xtitle in XTITLE):
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//span[contains(@id, "next-page")]/a/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace("Test du ", '').split(":")[0].replace('Test des ', '').replace('Test de ', '').replace('Rétro-test du ', '').replace('Retro-test express ', '').replace('Rétro-test ', '').replace('Tests – ', '').replace('Test ', '').replace('Preview du ', '').replace(' – preview', '').replace(' – Vidéo sponso', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('retro-test-', '').replace('test-', '')

    category = data.xpath('//a[contains(@href, "/category/") and @property="v:title"]/text()').string()
    if category:
        product.category = category.replace('Tests & Comparatifs', '').replace('Tests – Autres Marques', '').replace('Tests – autres marques', '').replace('Tests -', '').strip().title()

    if not product.category:
        product.category = 'Technologie'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    rev_json = data.xpath('//script[contains(., "dateCreated")]/text()').string()
    if rev_json:
        rev_json = simplejson.loads(rev_json)

        date = rev_json.get('datePublished')
        if date:
            review.date = date.split("T")[0]

        author = rev_json.get('author', {}).get('name')
        author_url = rev_json.get('authot', {}).get('url')
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

    if not review.authors:
        author = data.xpath('//section[contains(@id, "author")]/following-sibling::div[@class="block-head"]/h3/text()').string()
        if author:
            author = author.split(':')[-1].strip()
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="review-final-score"]/h3/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review-final-score"]//@style').string()

    if grade_overall:
        grade_overall = grade_overall.replace('width:', '').strip(' %')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[@class="review-item"]')
    for grade in grades:
        grade_name = grade.xpath('.//h5//text()').string(multiple=True)
        grade_val = grade.xpath('.//span/@style').string()
        if grade_name and grade_val:
            grade_name = grade_name.split(' - ')[0].strip()
            grade_val = grade_val.replace('width:', '').strip(' %')
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=100.0))

    pros = data.xpath('//li[strong[contains(., "Les plus")]]/text()[normalize-space(.)]').string(multiple=True)
    if pros:
            pros = pros.strip(' +-*.:;•,–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

    cons = data.xpath('//li[strong[contains(., "Les moins")]]/text()[normalize-space(.)]').string(multiple=True)
    if cons:
        cons = cons.strip(' +-*.:;•,–')
        if len(cons) > 1:
            review.add_property(type='cons', value=cons)

    summary = data.xpath('//div[@class="review-short-summary"]/p//text()').string(multiple=True)
    conclusion = data.xpath('//h3[regexp:test(., "conclusion", "i")]/following-sibling::p[preceding-sibling::h3[1][regexp:test(., "conclusion", "i")] and not(preceding::strong[regexp:test(., "Les plus|Les moins")] or contains(., "Voir la vidéo de "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[regexp:test(., "conclusion", "i")]]/following-sibling::p[not(preceding::strong[regexp:test(., "Les plus|Les moins")] or contains(., "Voir la vidéo de "))]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

        if summary:
            review.add_property(type='summary', value=summary)

    elif summary:
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//div[@class="entry"]/p[not(preceding::strong[regexp:test(., "Les plus|Les moins")] or preceding::h3[regexp:test(., "conclusion", "i")] or preceding::p/strong[regexp:test(., "conclusion", "i")] or contains(., "Voir la vidéo de ") or strong[regexp:test(., "conclusion", "i")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
