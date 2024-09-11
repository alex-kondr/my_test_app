from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.haus.de/test'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="css-1pip4vl"]')
    for cat in cats:
        name = cat.xpath('div[@class="css-60z25j"]/text()').string()

        sub_cats = cat.xpath('div/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = sub_cat.xpath('@href').string()
            session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "teaserbox")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_reviews, dict(context, url=url))

    next_url = data.xpath('//a[@rel="follow" and not(text())]/@href[contains(., "?page=")]').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_reviews(data, context, session):
    revs = data.xpath('//div[contains(@class, "paragraph-wrapper") and .//span[regexp:test(., "Platz \d+")]]')
    for i, rev in enumerate(revs, start=1):
        prod_numb = rev.xpath('.//span[regexp:test(., "Platz \d+")]/text()').string()
        prod_info = data.xpath('(//div[contains(@class, "chakra-stack") and contains(., "{prod_numb}")])[1]'.format(prod_numb=prod_numb)).first()

        if not prod_info:
            return

        product = Product()
        product.name = prod_info.xpath('.//div[@class="css-0"]/text()').string()
        product.url = prod_info.xpath('.//a[contains(@class, "chakra-link")]/@href').string()
        product.ssid = product.name.lower().replace(' ', '-').replace('(', '-').replace(')', '-').strip(' -')
        product.category = context['cat']

        review = Review()
        review.type = 'pro'
        review.title = data.xpath('//h1[contains(@class, "chakra-heading")]/text()').string()
        review.url = context['url']
        review.ssid = product.ssid

        date = data.xpath('//div[@data-testid="DateTimeValue"]/text()').string()
        if date:
            review.date = date.split()[0]

        grade_overall = prod_info.xpath('.//div[span[contains(., "Ø")]]/text()').string(multiple=True)
        if grade_overall:
            grade_overall = grade_overall.split('/')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

        if not grade_overall:
            grade_overall = rev.xpath('count(.//div[contains(@class, "chakra-stack")]/svg[contains(@class, "chakra-icon")])')
            if grade_overall:
                grade_half = rev.xpath('count(.//div[contains(@class, "chakra-stack")]/div/div[not(@class="css-1udpgqb")])')
                if grade_half:
                    grade_overall = grade_overall + .5

                review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

        grades = prod_info.xpath('.//div[@class="css-1s84675"]')
        grade_names = ['Qualität', 'Bedienkomfort/Handhabung', 'Schneidleistung']
        for grade, grade_name in zip(grades, grade_names):
            grade = grade.xpath('.//text()').string(multiple=True)
            review.grades.append(Grade(name=grade_name, value=float(grade), best=10.0))


        author = data.xpath('//a[contains(@href, "https://www.haus.de/autoren/") and text() and not(contains(., "Haus.de"))]/text()').string()
        author_url = data.xpath('//a[contains(@href, "https://www.haus.de/autoren/") and text() and not(contains(., "Haus.de"))]/@href').string()
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        pros = prod_info.xpath('.//li[span[contains(., "+")]]')
        for pro in pros:
            pro = pro.xpath('text()').string()
            if pro:
                pro = pro.lstrip(' +-.')
                review.add_property(type='pros', value=pro)

        cons = prod_info.xpath('.//li[span[contains(., "-")]]')
        for con in cons:
            con = con.xpath('text()').string()
            if con:
                con = con.lstrip(' +-.')
                review.add_property(type='cons', value=con)

        summary = data.xpath('//div[contains(@class, "chakra-container")]/div[contains(@class, "html-text text")]/p//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = rev.xpath('following-sibling::div[contains(@class, "paragraph-wrapper") and count(preceding-sibling::div[regexp:test(., "Platz \d+")])={i}]//p//text()'.format(i=i)).string(multiple=True)
        if excerpt:
            strings = []
            if 'Fazit:' in excerpt:
                strings = excerpt.split('Fazit:')
            elif 'Fazit :' in excerpt:
                strings = excerpt.split('Fazit :')

            if strings:
                excerpt = strings[0].strip()

                conclusion = ' '.join(strings[1:]).strip()
                review.add_property(type='conclusion', value=conclusion)

            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
