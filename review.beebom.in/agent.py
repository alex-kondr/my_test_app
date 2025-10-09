from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('https://beebom.com/category/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3[contains(@class, "title")]//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review – ')[0].split(' Review: ')[0].split(' – The Movie: ')[0].split(' Test: ')[0].replace('I Tested ', '').replace(' (Review)', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = 'Tech'

    product.url = data.xpath('//a[span[contains(text(), "Buy")]]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="view-card__authors"]//text()').string(multiple=True)
    author_url = data.xpath('//div[@class="view-card__authors"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-heading")]/div[@class="gradient"]/div[contains(@class, "gradient-score percent")]/div[contains(@class, "review-point")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[contains(@class, "review-point")]/text()').string()

    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[contains(@class, "review-points")]/div[contains(@class, "review-point")]')
    for grade in grades:
        grade_name = grade.xpath('.//div[contains(@class, "review-point-heading")]/text()').string()
        grade_val = grade.xpath('.//div[contains(@class, "review-point-content")]/text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[@class="beebom-single-review" and div[contains(text(), "Pros")]]//div[contains(@class, "review-item")]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="beebom-single-review" and div[contains(text(), "Cons")]]//div[contains(@class, "review-item")]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "Verdict|Should You Buy", "i")]/following-sibling::p[not(.//strong[contains(., "Buy from")])]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)


    excerpt = data.xpath('//h2[regexp:test(., "Verdict|Should You Buy", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content-container")]/p[not(.//strong[contains(., "Buy from")])]//text()').string(multiple=True)

    if excerpt:
        if 'Overall, ' in excerpt and not conclusion:
            excerpt, conclusion = excerpt.rsplit('Overall, ', 1)

            conclusion = conclusion.strip()[0].title() + conclusion.strip()[1:]
            review.add_property(type='conclusion', value=conclusion)

        summary = data.xpath('(//div[@class="review-verdict"])[1]//text()').string(multiple=True)
        if summary and conclusion:
            review.add_property(type='summary', value=summary)
        elif summary:
            review.add_property(type='conclusion', value=summary)

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
