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
    session.queue(Request('https://www.gamepur.com/reviews'), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "article-list")]/article/a')
    for rev in revs:
        title = rev.xpath('.//div[contains(@class, "info-title")]//text()').string(multiple=True).strip()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review – ')[0].split(' Review: ')[0].split('Review: ')[-1]
    product.url = context['url']
    product.ssid = data.xpath('//main/div/@data-id').string()

    manufacturer = data.xpath('//li[strong[contains(., "Developer")]]/text()').string()
    if manufacturer:
        product.manufacturer = manufacturer.strip(' :–')

    category = "Games|"
    platforms = data.xpath('//li[strong[contains(., "Platforms")]]/text()').string()
    if platforms:
        platforms = platforms.replace(' and ', ', ').replace(' & ', ', ').replace('at launch', '').replace('coming in March', '').replace('|', '\\').replace('/', ', ').strip(' –:').split(', ')
        for platform in platforms:
            category += platform.strip(' ,') + '/'

    product.category = category.strip('/| ')

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-bio__name")]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string().strip('+')
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_ssid))

    pros = data.xpath('//td[strong[contains(., "+")]]/following-sibling::td//text()')
    if not pros:
        pros = data.xpath('//td[strong[contains(., "+")]]/text()')
    for pro in pros:
        pro = pro.string(multiple=True).strip()
        if pro:
            review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//td[strong[contains(., "–") or contains(., "-")]]/following-sibling::td//text()')
    if not cons:
        cons = data.xpath('//td[strong[contains(., "–") or contains(., "-")]]/text()')
    for con in cons:
        con = con.string(multiple=True).strip()
        if con:
            review.properties.append(ReviewProperty(type='cons', value=con))

    grade_overall = data.xpath('//div[p[strong[regexp:test(., "final score", "i")]]]/p[contains(., "/")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//*[self::h2 or self::h3][regexp:test(., "final score", "i")]/following-sibling::*[self::h2 or self::h3][1]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    summary = data.xpath('//div[contains(@class, "content--subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('.//*[self::h2 or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")]/following-sibling::p[not(contains(., "Related :") or contains(., "Related:") or contains(., "Disclosure:") or contains(., "This article includes "))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "article-content")]/p[not(preceding-sibling::*[self::h2 or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")])][not(contains(., "Related :") or contains(., "Related:") or contains(., "Disclosure:") or contains(., "This article includes "))]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
