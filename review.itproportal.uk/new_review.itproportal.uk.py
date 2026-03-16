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
    session.queue(Request('https://www.itpro.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    page = data.xpath('//div[@class="flexi-pagination"]/span/text()').string()
    if not page or not page.isdigit() or int(page) != context.get('page', 1):
        return

    revs = data.xpath('//ul[contains(@class, "listing__list")]/li//a')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_page = int(page) + 1
    next_url = 'https://www.itpro.com/reviews/page/' + str(next_page)
    session.queue(Request(next_url), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(' review', '').replace(' Review', '').strip()
    product.url =  context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        if author_name and author_url:
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    grade_overall = data.xpath('//div[@class="rating"]/span[@class="chunk rating"]/@aria-label').string()
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('out of')[0]
        if float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[@class="procon__pros"]//li/p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="procon__cons"]//li/p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="news-article"]//p[contains(@class, "header")]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[@id="article-body"]/p[preceding-sibling::h2[contains(., "Is it worth it")]]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@id="article-body"]/p[not(preceding-sibling::h2[contains(., "Is it worth it")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
