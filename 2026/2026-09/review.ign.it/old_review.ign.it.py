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
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://it.ign.com/article/review'), process_category, {})


def process_category(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    cats = data.xpath('//ul[@class="filterlist"]/li[not(@class="all  active")]//a')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()
        if name and url:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="m"]/h3//a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()

    name = data.xpath('//div[@class="object-breadcrumbs"]/a/text()').string()
    if name == 'Cinema/TV' or name == 'Amazon':
        name = context['title'].strip()
    elif name == 'Online' or name == 'Mobile':
        name = context['title'].strip()

    product.name = name

    product.url = context['url']    # or data.xpath('//div[@class="object-breadcrumbs"]/a/@href').string() — all the reviews of the product
    product.manufacturer = data.xpath('//div[@class="meta"]//span[@class="txt"]/text()').string()
    product.ssid = product.url.split('/')[-1]

    category = context['cat'] + '|'
    plats = data.xpath('//li[@class="platform"]/@data-platform').strings()
    for plat in plats:
        plat_name = plat.replace('-', ' ').upper().strip()
        if plat_name:
            category += plat_name + '/'

    product.category = category.strip('|/ ')

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//div[@class="article-byline"]//span[contains(@class, "reviewer")]/a')
    for author in authors:
        author_name = author.xpath('text()').string()
        author_url = author.xpath('@href').string()     # page with all author's reviews
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author_name, ssid=author_ssid))

    summary = data.xpath('//h3[@id="id_deck"]/text()').string(multiple=True)
    if summary:
        context['summary'] = summary.strip()

    conclusion = data.xpath('//p[preceding-sibling::h3[regexp:test(., "verdetto", "i")]]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@id="id_text"]//text()[not(contains(., "Commento"))][not(ancestor::div[@id="ratingsBox"] or preceding::div[@id="ratingsBox"])][preceding::div[contains(text(), "Commento")]]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="details"]/div[contains(@id, "bottomline")]/text()').string(multiple=True)
    if conclusion:
        context['conclusion'] = conclusion.strip()

    excerpt = data.xpath('//div[@id="id_text"]/p[not(preceding::div[contains(text(), "Verdetto") or contains(text(), "Commento")])]//text()[not(contains(., "Commento"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="id_text"]//text()[not(ancestor::div[contains(text(), "Verdetto") or contains(text(), "Commento")] or preceding::div[contains(text(), "Verdetto") or contains(text(), "Commento")])][not(contains(., "Commento"))]').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion.strip(), '')

        context['excerpt'] = excerpt.strip()

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        page = 1
        title = review.title + " - Pagina " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url), process_review_next, dict(context, product=product, review=review, page=page+1))

    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data: Response, context: dict[str, str], session: Session)


def process_review_next(data: Response, context: dict[str, str], session: Session):
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
        name = grade.xpath('td[@class="ratingsBoxText"]//strong/text()').string()
        value = grade.xpath('td[@class="ratingsBoxScore"]/text()').string()
        if name and value:
            value = float(value.replace(',', '.'))
            review.grades.append(Grade(name=name, value=value, best=10.0))

    pros = data.xpath('//ul[@class="pros-cons-list"][contains(@id, "pros")]/li/text()').strings()
    for pro in pros:
        review.properties.append(ReviewProperty(type='pros', value=pro))

    cons = data.xpath('//ul[@class="pros-cons-list"][contains(@id, "cons")]/li/text()').strings()
    for con in cons:
        review.properties.append(ReviewProperty(type='cons', value=con))

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Pagina " + str(page)
        url = data.xpath('//link[@rel="canonical"]/@href').string()
        review.add_property(type='pages', value=dict(title=title, url=url))

        conclusion = data.xpath('//p[preceding-sibling::h3[regexp:test(., "verdetto", "i")]]/text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@id="id_text"]//text()[not(contains(., "Commento"))][not(ancestor::div[@id="ratingsBox"] or preceding::div[@id="ratingsBox"])][preceding::div[contains(text(), "Commento")]]').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//div[@class="details"]/div[contains(@id, "bottomline")]/text()').string(multiple=True)
        if conclusion:
            context['conclusion'] = conclusion.strip()

        excerpt = data.xpath('//div[@id="id_text"]/p[not(preceding::div[contains(text(), "Verdetto") or contains(text(), "Commento")])]//text()[not(contains(., "Commento"))]').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@id="id_text"]//text()[not(ancestor::div[contains(text(), "Verdetto") or contains(text(), "Commento")] or preceding::div[contains(text(), "Verdetto") or contains(text(), "Commento")])][not(contains(., "Commento"))]').string(multiple=True)
        if excerpt:
            if conclusion:
                excerpt = excerpt.replace(conclusion.strip(), '')

            context['excerpt'] += " " + excerpt.strip()

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, page=page + 1))
    else:
        if context.get('summary'):
            summary = context['summary']
            review.add_property(type='summary', value=summary)

        if context.get('conclusion'):
            conclusion = context['conclusion']
            review.add_property(type='conclusion', value=conclusion)

        if context.get('excerpt'):
            excerpt = context['excerpt']
            review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)
        session.emit(product)