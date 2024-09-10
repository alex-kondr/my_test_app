from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.haus.de/test'), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[@class="css-1pip4vl"]')
    for cat in cats:
        name = cat.xpath('div[@class="css-60z25j"]/text()').string()

        sub_cats = cat.xpath('div/a')
        for sub_cat in sub_cats:
            sub_name = sub_cat.xpath('text()').string()
            url = cat.xpath('@href').string()
            session.queue(Request(url), process_revlist, dict(cat=name + '|' + sub_name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "teaserbox")]')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_reviews, dict(context, url=url))

    next_url = data.xpath('//a[@rel="follow" and not(text())]/@href[contains(., "?page=")]').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    title = data.xpath('//h1[contains(@class, "chakra-heading")]/text()').string()

    product = Product()
    product.name = title.split('Test:')[-1].split('Test –')[-1]
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@data-testid="DateTimeValue"]/text()').string()
    if date:
        review.date = date.split()[0]

    author = data.xpath('//a[contains(@href, "https://www.haus.de/autoren/") and text() and not(contains(., "Haus.de"))]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.haus.de/autoren/") and text() and not(contains(., "Haus.de"))]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[contains(@class, "chakra-container")]/div[contains(@class, "html-text text")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//body//p//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//div[contains(@class, "paragraph-wrapper") and contains(., "Platz ")]')
    for i, rev in enumerate(revs, start=1):
        prod_info = data.xpath(f'(//div[contains(@class, "chakra-stack") and contains(., "Platz {i}")])[1]'.format(i=i))

        product = Product()
        product.name = prod_info.xpath('.//div[@class="css-0"]/text()').string()
        product.url = prod_info.xpath('.//a[contains(@class, "chakra-link")]/@href').string()
        product.ssid = product.name.lower().replace(' ', '-').replace('(', '-').replace(')', '-').strip(' -')
        product.category = context['cat']

        review = Review()
        review.type = 'pro'
        review.title = data.xpath('//h1[contains(@class, "chakra-heading")]/text()').string()

        date = data.xpath('//div[@data-testid="DateTimeValue"]/text()').string()
        if date:
            review.date = date.split()[0]

        grade_overall = rev.xpath('count(.//div[contains(@class, "chakra-stack")]/svg[contains(@class, "chakra-icon")])')
        if grade_overall:
            grade_half = rev.xpath('count(.//div[contains(@class, "chakra-stack")]//div[@class="css-1oacjwe"])')
            grade_overall = grade_overall + grade_half / 2
            review.grades.append(Grade(type='overall', value=grade_overall, value=5.0))

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
            review.add_property(type='pros', value=pro)

        cons = prod_info.xpath('.//li[span[contains(., "-")]]')
        for con in cons:
            con = con.xpath('text()').string()
            review.add_property(type='cons', value=con)

        summary = data.xpath('//div[contains(@class, "chakra-container")]/div[contains(@class, "html-text text")]/p//text()').string(multiple=True)
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = rev.xpath(f'following-sibling::div[contains(@class, "paragraph-wrapper") and count(preceding-sibling::div[contains(., "Platz ")])={i}]//p//text()'.format(i=i)).string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
