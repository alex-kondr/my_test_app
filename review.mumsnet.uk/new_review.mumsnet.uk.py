from tkinter.tix import Tree
from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request('https://www.mumsnet.com/h/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "flex pt-6")]/div[p]')
    for rev in revs:
        title = rev.xpath('p[contains(@class, "font-bold")]/text()').string()
        cats = rev.xpath('div/a[not(regexp:test(., "review", "i"))]/text()').strings().replace(' | ', '|')
        url = rev.xpath('a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, cats=cats, url=url))


def process_review(data, context, session):
    prods = data.xpath('//div[@class="mt-8" and div[contains(@class, "flex my-3")]]')
    if prods:
        process_reviews(data, context, session)
        return

    product = Product()
    product.name = context['title'].split('review')[0].replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[contains(., "Buy now from Amazon")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "Buy now")]/@href').string()
    if not product.url:
        product.url = context["url"]

    if context.get('cats'):
        product.category = '|'.join(context['cats'])

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date_json = data.xpath('//script[contains(., "datePublished")]/text()').string()
    if date_json:
        review.date = simplejson.loads(date_json).get('datePublished')
    else:
        date = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]/text()').string(multiple=True)
        if date:
            review.date = date.split('updated ')[-1]

    author = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]//a/text()').string()
    author_url = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
            review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('count(//div[div[contains(@id, "rating")] and contains(., "Our rating")]//use[contains(@href, "#star-solid")])')
    grade_overall_half = data.xpath('count(//div[div[contains(@id, "rating")] and contains(., "Our rating")]//use[contains(@href, "#star-sharp-half-stroke")])')
    if grade_overall:
        if grade_overall_half:
            grade_overall += grade_overall_half / 2
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('//p[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+") and contains(., "Overall")]//text()').string(multiple=True)
        if grade_overall:
            grade_overall = grade_overall.split(':')[-1].split('/')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//div[div[contains(@id, "rating")] and not(contains(., "Our rating"))]')
    for grade in grades:
        grade_name = grade.xpath('div[contains(@class, "font-bold")]/text()').string().strip(' :')
        grade_val = grade.xpath('count(.//use[contains(@href, "#star-solid")])')
        grade_val_half = grade.xpath('count(.//use[contains(@href, "#star-sharp-half-stroke")])')
        if grade_val_half:
            grade_val += grade_val_half / 2

        if grade_name and grade_val:
            review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    if not grades:
        grades = data.xpath('//p[regexp:test(normalize-space(.), "\d+\.?\d? ?/ ?\d+") and not(contains(., "Overall"))]')
        for grade in grades:
            grade_name, grade_val = grade.xpath('.//text()').string(multiple=True).split(':')
            grade_val = grade_val.split('/')[0]
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//*[contains(., "What we love") or contains(., "What we like") or contains(., "Pros")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//*[contains(., "What to know") or contains(., "What we don’t like") or contains(., "What we don\'t like") or contains(., "Cons")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="mt-4 text-xl prose"]/p//text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Our verdict") or contains(., "Our final verdict")]/following-sibling::p[not(contains(., "rating:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//div[@class="mt-8" and contains(., "Our verdict")]/following-sibling::div/div[@class="prose"])[1]/p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="mt-8"]/div[@class="prose"]/p[not(.//a[contains(., "Buy now from")] or contains(., "Read next:"))][not(preceding::text()[1][contains(., "Key specs")])][not(preceding::text()[1][contains(., "About Mumsnet Reviews")])][not(preceding::text()[contains(., "About the author")])][not(contains(., "Related:"))][not(contains(., "rating:") or preceding::h2[1][contains(., "Our verdict") or contains(., "Our final verdict") or contains(., "About")])]//text()').string(multiple=True)
    if excerpt:

        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    prods = data.xpath('//div[@class="mt-8" and div[contains(@class, "flex my-3")]]')
    for prod in prods:
        product = Product()
        product.name = prod.xpath('.//h2/text()').string().replace(' Review', '').strip()
        product.ssid = context['url'].split('/')[-1].replace('-review', '')
        product.category = 'Tech'

        product.url = prod.xpath('.//a[contains(., "Buy now from Amazon") or contains(., "Buy now from Mamas & Papas") or contains(., "Buy now from Kiddies Kingdom")]/@href').string()
        if not product.url:
            product.url = context["url"]

        if context.get('cats'):
            product.category = '|'.join(context['cats'])

        review = Review()
        review.type = 'pro'
        review.title = prod.xpath('.//span[@class="h4"]/text()').string()
        review.url = context['url']
        review.ssid = product.ssid

        date_json = data.xpath('//script[contains(., "datePublished")]/text()').string()
        if date_json:
            review.date = simplejson.loads(date_json).get('datePublished')
        else:
            date = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]/text()').string(multiple=True)
            if date:
                review.date = date.split('updated ')[-1]

        author = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]//a/text()').string()
        author_url = data.xpath('//p[@class="mt-4 text-gray-600 text-sm"]//a/@href').string()
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = prod.xpath('count((.//div[use])[1]/use[contains(@href, "#star-solid")])')
        grade_overall_half = prod.xpath('count((.//div[use])[1]/use[contains(@href, "#star-sharp-half-stroke")])')
        if grade_overall:
            if grade_overall_half:
                grade_overall += grade_overall_half / 2
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        pros = prod.xpath('.//*[contains(., "What we love") or contains(., "What we like") or contains(., "Pros")]/following-sibling::ul[1]/li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

        cons = prod.xpath('.//*[contains(., "What to know") or contains(., "What we don’t like") or contains(., "What we don\'t like") or contains(., "Cons")]/following-sibling::ul[1]/li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if len(con) > 1:
                review.add_property(type='cons', value=con)

        summary = data.xpath('//div[@class="mt-4 text-xl prose"]/p//text()').string()
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = prod.xpath('.//div[contains(., "Our verdict")]/following-sibling::p[not(contains(., "Read next:") or contains(., "Related:") or contains(., "Tested by"))]//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
