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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://memeburn.com/gearburn/category/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[contains(@id, "post-") and contains(@class, "category-reviews")]')
    for rev in revs:
        ssid = rev.xpath('@id').string()
        title = rev.xpath('.//h2[contains(@class, "title")]/a/text()').string()
        url = rev.xpath('.//h2[contains(@class, "title")]/a/@href').string()
        session.queue(Request(url), process_review, dict(title=title, ssid=ssid, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('We review: ', '').split(' review: ')[0].split(' review, ')[0].split(' review |')[0].split(' Review: ')[0].split(' review — ')[0].replace(' [Review]', '').replace(' reviews:', '').replace(': we review', '').replace(' reviewed', '').replace(' review', '').replace('Reviewed: ', '').replace('Reviewed — ', '').replace('Review: ', '').replace('Reviewing ', '').strip()
    product.url = context['url']
    product.ssid = context['ssid'].replace('post-', '')

    category = data.xpath('//header[@class="entry-header"]//span[@class="category"]/text()').string()
    if category:
        product.category = category.replace('News', '').strip()
    else:
        product.category = 'Tech'

    platform = data.xpath('//strong[contains(., "Platform")]/following-sibling::text()').string()
    if platform:
        product.category = 'Games|' + platform.strip(' :')

    manufacturer = data.xpath('//strong[contains(., "Developer")]/following-sibling::text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.strip(' :')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "author") and contains(text(), "By")]/span/span[contains(@class, "author")]//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "author") and contains(text(), "By")]/span/span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Score:")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('/')[0].split('out')[0].strip().split()[-1]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//p[contains(strong, "What we like")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(strong, "What we don’t like")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h3[regexp:test(., "verdict", "i")]/following-sibling::p[not(regexp:test(., "Read more:|Image credits:|Feature image") or preceding::strong[regexp:test(., "Who it’s for|What we like|What we don’t like")] or strong[regexp:test(., "Who it’s for|What we like|What we don’t like")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[regexp:test(strong, "verdict", "i")]/following-sibling::p[not(regexp:test(., "Read more:|Image credits:|Feature image") or preceding::strong[regexp:test(., "Who it’s for|What we like|What we don’t like")] or strong[regexp:test(., "Who it’s for|What we like|What we don’t like")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Verdict:")]//text()[not(contains(., "Verdict"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(strong, "Who it’s for")]/following-sibling::p[1]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion.strip(' :'))

    excerpt = data.xpath('//div[contains(@class, "single__entry-content")]/p[not(regexp:test(., "Read more:|Image credits:|Feature image|Verdict:|Score:") or preceding::strong[regexp:test(., "Who it’s for|What we like|What we don’t like|Verdict", "i")] or strong[regexp:test(., "Who it’s for|What we like|What we don’t like|Verdict", "i")] or preceding::h3[regexp:test(., "verdict", "i")] or @style)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
