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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://attackofthefanboy.com/category/reviews/'), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//article[contains(@class, "wp-block-gamurs-article-tile")][not(ancestor::div[contains(@class, "sidebar-container")])]/a')
    for rev in revs:
        title = rev.xpath('.//div[contains(@class, "article-info-title")]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//h2[@class="review-title"]/text()').string() or data.xpath('//div[@class="wp-block-gamurs-review-summary__title"]/text()').string()
    if not product.name:
        product.name = context['title'].replace(' Review', '')

    product.manufacturer = data.xpath('//li[contains(., "Developed")]/text()').string(multiple=True) or data.xpath('//li[contains(., "Published")]/text()').string(multiple=True)

    category = 'Games|'
    plats = data.xpath('//li[contains(., "Available On:")]/text()').string(multiple=True)
    if not plats:
        plats = data.xpath('//div[contains(., "Reviewed on ") and contains(@class, "summary__disclaimer")]/text()').string()
    if plats:
        plats = plats.split(' on ')[-1].split(',')
        for plat in plats:
            plat_name = plat.strip()
            if plat_name:
                category += plat_name.replace('/', '\\').replace('|', '\\').replace('and ', '') + '/'

    genres = data.xpath('//li[contains(., "Genre:")]/text()').string(multiple=True)
    if genres:
        category = category.strip('/') + '|'
        genres = genres.split(',')
        for genre in genres:
            genre_name = genre.strip()
            if genre_name:
                category += genre_name + '/'

    product.category = category.strip('|/ ')

    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]

    review = Review()
    review.title = context['title']
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "metadata__name")]/div').first()
    if author:
        author_name = author.xpath('text()').string()
        author_ssid = author.xpath('@data-author').string()
        if author_name and author_ssid:
            review.authors.append(Person(name=author_name, ssid=author_ssid))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath('//li[contains(., "Score:")]/text()').string(multiple=True) or data.xpath('//div[contains(@class, "number-rating")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        if grade_overall.strip():
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//h2[contains(@class, "summary")]/text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath('//div/p[preceding-sibling::*[self::h2 or self::h3][regexp:test(., "verdict", "i") or regexp:test(., "final thoughts", "i")]][not(contains(., "This article was updated"))]//text()').string(multiple=True)
    conclusion_2 = data.xpath('//li[contains(@class, "verdict")]/text()').string(multiple=True) or data.xpath('//div[@class="wp-block-gamurs-review-summary__text"]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "article-content") or contains(@class, "entry-content")]/p[strong[regexp:test(., "verdict:", "i") or regexp:test(., "final thoughts", "i")]]//text() | //div[contains(@class, "entry-content")]/p[preceding::p[strong[regexp:test(., "verdict:", "i") or regexp:test(., "final thoughts", "i")]]][not(contains(., "This article was updated"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = conclusion_2
    if conclusion:
        if conclusion_2 and conclusion_2 not in conclusion:
            conclusion += conclusion_2

        conclusion = conclusion.rstrip('"').strip()
        if conclusion:
            review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath('//div[contains(@class, "article-content") or contains(@class, "entry-content")]//p[not(contains(., "This article was updated") or regexp:test(., "verdict:", "i"))][not(preceding::*[self::h2 or self::h3 or self::p[strong]][regexp:test(., "verdict", "i")])][not(contains(., "<span"))]//text()').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()
        if conclusion_2:
            excerpt = excerpt.replace(conclusion_2, '').strip()

        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)
        session.emit(product)
