from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.benchmark.pl/brkReviewFrontend/getArticles?page=1", force_charset="utf-8", use='curl', max_age=0), process_prodlist, dict())


def process_prodlist(data, context, session):
    prods = data.xpath('//h2[@class="bse-title"]/parent::div[.//div[@class="listing-label listing-label--article"]]')
    for prod in prods:
        cat = prod.xpath('.//span[@class="bse-cat"]/a/span/text()').string()
        if cat and not cat.lower().startswith("gry"):
            title = prod.xpath('.//h2[@class="bse-title"]//a/text()').string()
            url = prod.xpath('.//h2[@class="bse-title"]//a/@href').string()
            session.queue(Request(url, use="curl", force_charset="utf-8", max_age=0), process_review, dict(cat=cat, url=url, title=title))

    if prods:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.benchmark.pl/brkReviewFrontend/getArticles?page=' + str(next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_prodlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('-', '–').split(" – ")[0].split('Testujemy ')[-1]
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].replace('.html', '')
    product.category = context['cat']

    review = Review()
    review.title = context['title']
    review.url = context["url"]
    review.ssid = product.ssid
    review.type = "pro"

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath("//a[@rel='author']|//span[@class='authorship-name__link']").first()
    if author:
        author_name = author.xpath('span[contains(@class, "first")]/text() | span[contains(@class, "last")]/text()').string(multiple=True)
        author_url = author.xpath("@href").string()
        if author_name and author_url:
            review.authors.append(Person(name=author_name, ssid=author_name, profile_url=author_url))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath("//p[@class='rating']/text()").string()
    if not grade_overall:
        grade_overall = data.xpath('//ul[@data-rating]/@data-rating').string()
    if not grade_overall:
        grade_overall = data.xpath("//p[@class='rating']/span/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//div[@class='rating']//li[@class='rating__note']/text()").string()

    if grade_overall:
        value = grade_overall.replace(',', '.').split('/')[0]
        review.grades.append(Grade(type="overall", value=float(value), best=5.0))

    pros = data.xpath("(//div[@class='plus-minus']//div[text()='Plusy' or text()='Pros' or ./span/text()='Plusy' or ./span/text()='Pros']/following-sibling::ul|//h3[contains(.,'Plusy')]/following-sibling::ul[following-sibling::h3])[1]/li")
    if not pros:
        pros = data.xpath('(//h3[contains(., "Warto kupić, jeśli:")]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath("//div[@class='pdc_prosNcons']/span[@class='minus']/preceding-sibling::p/text()").string()
        if pros:
            pros = pros.replace("- ", '').split(';')
            for pro in pros:
                pro = pro.strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='cons', value=pro)

    cons = data.xpath("(//div[@class='plus-minus']//div[text()='Minusy' or text()='Minuses' or ./span/text()='Minusy' or ./span/text()='Minuses']/following-sibling::ul|//h3[contains(.,'Minusy')]/following-sibling::ul)[1]/li")
    if not cons:
        cons = data.xpath('(//h3[contains(., "Nie warto, jeśli:")]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath("//div[@class='pdc_prosNcons']/span[@class='minus']/following-sibling::p/text()").string()
        if cons:
            cons = cons.replace("- ", '').split(';')
            for con in cons:
                con = con.strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    summary = data.xpath("//div[@class='article__preamble']//text()").string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type="summary", value=summary.strip())

    excerpt = data.xpath('//*[self::h2 or self::h3 or self::h4][regexp:test(normalize-space(.),"czy.+warto|czy.+wybór", "i")]/preceding::p[not(.//em or parent::div[@class="article__preamble"])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="content"]/p[not(.//em or parent::div[@class="article__preamble"])]//text()').string(multiple=True)

    next_page = data.xpath("//div[@class='readNext center' or @class='readNext right']//a/@href").string()
    page_title = data.xpath("//div[@class='bbh-p-head']//h1//text()").string()
    if next_page:
        review.add_property(type="pages", value=dict(url=context['url'], title=page_title))

        session.do(Request(next_page, use="curl", force_charset="utf-8", max_age=0), process_lastpage, dict(product=product, review=review, excerpt=excerpt))

    else:
        conclusion = data.xpath("//*[self::h2 or self::h3 or self::h4][regexp:test(normalize-space(.),'czy.+warto|czy.+wybór', 'i')]/following-sibling::p[following-sibling::h3 or following-sibling::h2 or following-sibling::h4 or following-sibling::div][last() and not(.//em)]//text()").string(multiple=True)
        if conclusion:
            conclusion = conclusion.replace(u'\uFEFF', '').strip()
            review.add_property(type="conclusion", value=conclusion)

        if excerpt:
            excerpt = excerpt.replace(u'\uFEFF', '').strip()
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

            session.emit(product)


def process_lastpage(data, context, session):
    review = context["review"]

    page_title = data.xpath("//div[@class='bbh-p-head']//h1//text()").string()
    review.add_property(type="pages", value=dict(url=data.response_url, title=page_title))

    next_url = data.xpath("//div[@class='readNext center' or @class='readNext right']//a/@href").string()
    if next_url:
        session.do(Request(next_url, use="curl", force_charset="utf-8", max_age=0), process_lastpage, dict(context, review=review))

    elif context['excerpt']:
        if page_title and "podsumowanie" in page_title.lower():
            conclusion = data.xpath("//div[@id='content']/p//text()").string(multiple=True)
            if conclusion:
                conclusion = conclusion.replace(u'\uFEFF', '').strip()
                review.add_property(type="conclusion", value=conclusion)

        else:
            excerpt = data.xpath("//div[@id='content']/p//text()").string(multiple=True)
            if excerpt:
                context['excerpt'] += ' ' + excerpt

        context['excerpt'] = context['excerpt'].replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=context['excerpt'])

        product= context['product']
        product.reviews.append(review)

        session.emit(product)
