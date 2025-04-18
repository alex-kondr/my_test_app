from agent import *
from models.products import *
import re


XCAT = ['Accueil']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.clubic.com/test-produit/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[p[@data-testid="meta-label"]]')
    for rev in revs:
        title = rev.xpath('p/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    revs = data.xpath('//div[@class="legacy-rating-block"]')
    rev_name = data.xpath('//div[contains(@class, "content")]/h2[contains(@class, "title") and not(regexp:test(., "Tableau|Conclusion"))]/following-sibling::div[count(preceding-sibling::h2[contains(@class, "title")])=1][contains(@class, "body")]//h4[contains(@class, "title")]/text()').string()
    if len(revs) > 1 and rev_name:
        process_reviews(data, context, session)
        return

    product = Product()

    product.name = data.xpath('//div[contains(@class, "fFEfHL")]/a[@class="un-styled-linked"]/text()').string()
    if not product.name:
        product.name = data.xpath('//div[@class="legacy-rating-block"]//h3/text()').string()
    if not product.name:
        product.name = context['title'].replace('Test :', '').replace('Test:', '').replace('TEST :', '').replace('TEST:', '').split(':')[0].split('|')[-1].replace('(Tech Preview)', '').replace('Test ', '').replace('TEST ', '').strip()

    product.url = data.xpath('//a[contains(@href, "https://redirect.affilizz.com")]/@href').string()
    if not product.url:
        product.url = context['url']

    prod_ssid = re.search(r'-\d+-', context['url'])
    if prod_ssid:
        product.ssid = prod_ssid.group().strip('-')
    else:
        product.ssid = context['url'].split('/')[-1].replace('.html', '').replace('test-', '')

    cats = data.xpath('//ul[@id="breadcrumb-list"]/li/a/text()').strings()
    if cats:
        category = ''
        for cat in cats:
            if 'Test' not in cat and cat not in XCAT and not any([cat_ for cat_ in cat.split() if cat_ in category]):
                category += cat + '|'

        category = category.strip(' |')
        if len(category) > 1:
            product.category = category

    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://www.clubic.com/auteur/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.clubic.com/auteur/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].split('-')[0]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(@class, "mod-dark")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('(//div[normalize-space(text())="Sous-notes"]/following-sibling::div)[1]/div')
    for grade in grades:
        grade_name = grade.xpath('div/text()').string()
        grade_val = grade.xpath('span/text()').string()
        if grade_name and grade_val and grade_val.isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('(//div[contains(., "Les plus")]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' -.()')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('(//div[contains(., "Les moins")]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' -.()')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "row")]/div/p/strong//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[div[contains(., "Conclusion")]]/following-sibling::div/div/p//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "row")]/div/p[not(strong)]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//div[contains(@class, "content")]/h2[contains(@class, "title") and not(regexp:test(., "Tableau|Conclusion|Test"))]')
    for i, rev in enumerate(revs, start=1):
        product = Product()
        product.name = rev.xpath('following-sibling::div[count(preceding-sibling::h2[contains(@class, "title")])={}][contains(@class, "body")]//h4[contains(@class, "title")]/text()'.format(i)).string()
        product.ssid = product.name.lower().replace(' ', '-')
        product.url = context['url']

        cats = data.xpath('//ul[@id="breadcrumb-list"]/li/a/text()').strings()
        if cats:
            category = ''
            for cat in cats:
                if 'Test' not in cat and cat not in XCAT and not any([cat_ for cat_ in cat.split() if cat_ in category]):
                    category += cat + '|'

            category = category.strip(' |')
            if len(category) > 1:
                product.category = category

        if not product.category:
            product.category = 'Tech'

        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.ssid = product.ssid
        review.url = product.url

        date = data.xpath('//meta[@property="article:published_time"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//a[contains(@href, "https://www.clubic.com/auteur/")]/text()').string()
        author_url = data.xpath('//a[contains(@href, "https://www.clubic.com/auteur/")]/@href').string()
        if author and author_url:
            author_ssid = author_url.split('/')[-1].split('-')[0]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following-sibling::div[count(preceding-sibling::h2[contains(@class, "title")])={}][contains(@class, "body")]//span[contains(@class, "rating-block__score")]//em/text()'.format(i)).string()
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

        grades = rev.xpath('following-sibling::div[count(preceding-sibling::h2[contains(@class, "title")])={}][contains(@class, "body")]//div[contains(@class, "rating-block__cell--details")]//p[contains(@class, "progress")]'.format(i))
        for grade in grades:
            grade = grade.xpath('span/text()').strings()
            if len(grade) == 2:
                grade_name, grade_val = grade
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

        pros = rev.xpath('(following-sibling::div[count(preceding-sibling::h2[contains(@class, "title")])={}][contains(@class, "body")]//ul[contains(@class, "list--pros")])[1]/li'.format(i))
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True).strip(' -.()')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

        cons = rev.xpath('(following-sibling::div[count(preceding-sibling::h2[contains(@class, "title")])={}][contains(@class, "body")]//ul[contains(@class, "list--cons")])[1]/li'.format(i))
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True).strip(' -.()')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

        summary = data.xpath('//div[contains(@class, "row")]/div/p/strong//text()').string(multiple=True)
        if summary:
            summary = summary.replace(u'\uFEFF', '').strip()
            review.add_property(type='summary', value=summary)

        conclusion = rev.xpath('following-sibling::h3[contains(., "Conclusion")]/following-sibling::text()[count(preceding-sibling::h2[contains(@class, "title")])={}]'.format(i)).string(multiple=True)
        if conclusion:
            conclusion = conclusion.replace(u'\uFEFF', '').strip()
            review.add_property(type='conclusion', value=conclusion)

        excerpt = rev.xpath('following-sibling::h3[contains(., "Conclusion")][count(preceding-sibling::h2[contains(@class, "title")])=2]/preceding-sibling::text()[count(preceding-sibling::h2[contains(@class, "title")])=2]').string(multiple=True)
        if not excerpt:
            excerpt = rev.xpath('following-sibling::text()[count(preceding-sibling::h2[contains(@class, "title")])={}]'.format(i)).string(multiple=True)

        if excerpt:
            excerpt = excerpt.replace(u'\uFEFF', '').strip()
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(excerpt)

            session.emit(product)
