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


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://es.ign.com/article/review'), process_category, {})


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="filterlist"]/li[not(contains(@class, "all"))]')
    for cat in cats:
        name = cat.xpath('.//span/text()').string(multiple=True)
        url = 'https://es.ign.com/article/review?keyword__type=' + cat.xpath('@class').string()

        if name and url:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="m"]/h3/a')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.replace('/review', '').split('/')[-2]
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[@class="meta"]//span[@class="txt"]/text()').string()

    product.name = data.xpath('//div[@class="object-breadcrumbs"]/a/text()').string()
    if not product.name:
        product.name = context['title'].replace(' - Análisis', '').strip()

    platforms = data.xpath('//li[@class="platform"]/@data-platform').join('/')
    if platforms:
        product.category = 'Juegos|' + platforms.replace('-', ' ').upper().strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//div[@class="article-byline"]//span[contains(@class, "reviewer")]/a')
    for author in authors:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    summary = data.xpath('//h3[@id="id_deck"]/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[preceding-sibling::h3[regexp:test(., "veredicto", "i")]]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@id="id_text"]//text()[not(contains(., "El veredicto"))][not(ancestor::div[@id="ratingsBox"] or preceding::div[@id="ratingsBox"])][preceding::div[contains(text(), "Commento")]]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="details"]/div[contains(@id, "bottomline")]/text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    context['excerpt'] = data.xpath('//div[@id="id_text"]/p[not(preceding::div[contains(text(), "veredicto") or contains(text(), "Commento")])]//text()[not(contains(., "Commento"))]').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//div[@id="id_text"]//text()[not(ancestor::div[contains(text(), "El veredicto")] or preceding::div[contains(text(), "El veredicto")])][not(contains(., "El veredicto"))]').string(multiple=True)

    pages = data.xpath('//div[@class="paginator"]/a[contains(@class, "page")]')
    if pages:
        for page in pages:
            title = page.xpath('@title').string()
            page_url = page.xpath('@href').string()
            review.add_property(type='pages', value=dict(title=title, url=page_url))

        session.do(Request(page_url), process_review_last, dict(context, product=product, review=review, pages=True))

    else:
        context['product'] = product
        context['review'] = review
        process_review_last(data: Response, context: dict[str, str], session: Session)


def process_review_last(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    review = context['review']

    grade_overall = data.xpath('//div[@class="review"]//figure//span/div/text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//tr[@class="ratingsBoxECRow"]/td//div[@class="ratingsBoxScoreOvText"]/text()').string()

    if grade_overall:
        grade_overall = float(grade_overall.replace(',', '.'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    grades = data.xpath('//table[@id="ratingsBoxTable"]/tbody/tr[not(@class)]')
    for grade in grades:
        grade_name = grade.xpath('td[@class="ratingsBoxText"]//strong/text()').string()
        grade_val = grade.xpath('td[@class="ratingsBoxScore"]/text()').string()
        if grade_name and grade_val:
            grade_val = float(grade_val.replace(',', '.'))
            review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    pros = data.xpath('//ul[@class="pros-cons-list"][contains(@id, "pros")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="pros-cons-list"][contains(@id, "cons")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if context.get('page'):
        conclusion = data.xpath('//p[preceding-sibling::h3[regexp:test(., "veredicto", "i")]]/text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@id="id_text"]//text()[not(contains(., "El veredicto"))][not(ancestor::div[@id="ratingsBox"] or preceding::div[@id="ratingsBox"])][preceding::div[contains(text(), "Commento")]]').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="details"]/div[contains(@id, "bottomline")]/text()').string(multiple=True)

        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

        excerpt = data.xpath('//div[@id="id_text"]/p[not(preceding::div[contains(text(), "El veredicto")])]//text()[not(contains(., "El veredicto"))]').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@id="id_text"]//text()[not(ancestor::div[contains(text(), "El veredicto")] or preceding::div[contains(text(), "El veredicto")])][not(contains(., "El veredicto"))]').string(multiple=True)

        if excerpt:
            if conclusion:
                excerpt = excerpt.replace(conclusion, '').strip()

            context['excerpt'] += " " + excerpt

    if context['excerpt']:
        review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
