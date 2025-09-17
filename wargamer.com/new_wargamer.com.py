from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.wargamer.com/'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[not(preceding-sibling::a[text()="About"])]/li[@class="menu-item"]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="link-title"]')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if 'Best ' in title or 'The best ' in title:
            session.queue(Request(url), process_reviews, dict(context, title=title, url=url))
        else:
            session.queue(Request(url), process_review, dict(context, title=title, url=url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(" Review –")[0].split(' review –')[0].replace('review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@name="parsely-pub-date"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="verdict-score"]//@src').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[-1].replace('.svg', '')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="pros"]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@id="article-details"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Should you buy")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[@class="summary"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Should you buy")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(contains(., "for more news on"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_reviews(data, context, session):
    revs = data.xpath('//div[contains(@id, "jump")]')
    for rev in revs:
        product = Product()
        product.name = rev.xpath('.//h2//text()').string(multiple=True)
        product.url = context['url']
        product.ssid = product.name.lower().replace(' ', '_')
        product.category = context['cat']

        review = Review()
        review.type = 'pro'
        review.title = context['title']
        review.url = product.url
        review.ssid = product.ssid

        date = data.xpath('//meta[@name="parsely-pub-date"]/@content').string()
        if date:
            review.date = date.split('T')[0]

        author = data.xpath('//a[@rel="author"]/text()').string()
        author_url = data.xpath('//a[@rel="author"]/@href').string()
        if author and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

        pros = rev.xpath('.//div[@class="to-buy"]//li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            review.add_property(type='pros', value=pro)

        cons = rev.xpath('.//div[@class="to-avoid"]//li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            review.add_property(type='cons', value=con)

        conclusion = rev.xpath('.//h3//text()').string(multiple=True)
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        excerpt = rev.xpath('.//p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
