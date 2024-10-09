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
    session.queue(Request('https://www.gamepur.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "article-info-title")]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    title = data.xpath('//h1[contains(@class, "content--title")]//text()').string(multiple=True)

    product = Product()
    product.name = title.split(' Review – ')[0].split(' Review: ')[0].split('Review: ')[-1].split(' review – is')[0].split(' review: ')[0].replace('Review – ', '').replace(' – Review', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = data.xpath('//div/@data-id').string()

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
    review.type = 'pro'
    review.title = title
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@class, "author-bio__name")]').first()
    if author:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string().strip('+')
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    pros = data.xpath('//td[strong[contains(., "+")]]/following-sibling::td//text()')
    if not pros:
        pros = data.xpath('//td[strong[contains(., "+") and not(contains(., "-"))]]/text()')

    for pro in pros:
        pro = pro.string(multiple=True).strip(' +-–')
        if pro:
            review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[contains(@class, "_pros-wrapper")]//li')
        for pro in pros:
            pro = pro.xpath('.//text()').string(multiple=True)
            if pro:
                pro = pro.strip(' +-–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[strong[contains(., "–") or contains(., "-")]]/following-sibling::td//text()')
    if not cons:
        cons = data.xpath('//td[strong[contains(., "–") or contains(., "-")]]/text()')

    for con in cons:
        con = con.string(multiple=True).strip(' +-–')
        if con:
            review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[contains(@class, "_cons-wrapper")]//li')
        for con in cons:
            con = con.xpath('.//text()').string(multiple=True)
            if con:
                con = con.strip(' +-–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    grade_overall = data.xpath('//div[p[strong[regexp:test(., "final score", "i")]]]/p[contains(., "/")]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//*[self::h2 or self::h3][regexp:test(., "final score", "i")]/following-sibling::*[self::h2 or self::h3][1]/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//div[contains(@class, "rating")]//text()').string(multiple=True)

    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    summary = data.xpath('//div[contains(@class, "content--subtitle")]//text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('.//*[self::h2 or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")]/following-sibling::p[not(contains(., "Related :") or contains(., "Related:") or contains(., "Disclosure:") or contains(., "This article includes "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "The Verdict")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//p[contains(., "The Verdict")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article-content")]/p[not(preceding-sibling::*[self::h2 or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "conclusion", "i") or regexp:test(., "final thoughts", "i")])][not(contains(., "Related :") or contains(., "Related:") or contains(., "Disclosure:") or contains(., "This article includes "))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
