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
    session.queue(Request('https://www.moviefone.com/movies/reviews/', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "movie-reviews-image")]/a/@href')
    for rev in revs:
        url = rev.string()
        session.queue(Request(url, max_age=0), process_review_info, dict())

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review_info(data, context, session):
    strip_namespace(data)

    name = data.xpath('//h1[contains(@class, "title")]/text()').string()
    prod_url = data.xpath('//a[contains(text(), "Official Website")]/@href').string()
    manufacturer = data.xpath('//div[strong[contains(text(), "Production Companies:")]]/span/text()').string()

    rev_url = data.xpath('//h2/a[contains(text(), " Review")]/@href[contains(., "movie-review")]').string()
    if rev_url:
        session.do(Request(rev_url, max_age=0), process_review, dict(url=rev_url, prod_url=prod_url, manufacturer=manufacturer, name=name))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = data.xpath('//a[contains(@class, "info-title")]/text()').string() or context['name']
    product.ssid = data.xpath('//article[contains(@id, "article-")]/@id').string().split('-')[-1]
    product.category = 'Movie'
    product.manufacturer = context['manufacturer']

    product.url = context['prod_url']
    if not product.url:
        product.url = context['url']

    genres = data.xpath('//a[@class="movie-rating-genre"]/text()').join('/')
    if genres:
        product.category += '|' + genres

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "article-title")]/text()').string()
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//a[@class="articlehead-date"]/text()').string()

    author = data.xpath('//div[@class="articlehead-author"]//text()').string()
    author_url = data.xpath('//div[@class="articlehead-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[div[contains(., "Review Score")]]/@data-score').string()
    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., " out of 100")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., " out of 10")]//text()').string(multiple=True)

    if grade_overall:
        if ' out of 100' not in grade_overall and ' out of 10' in grade_overall:
            grade_overall = grade_overall.split('score of ')[-1].split(' out of ')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        else:
            grade_overall = grade_overall.split('score of ')[-1].split(' out of ')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[div[contains(., "Audience Score")]]/@data-score').string()
    if grades:
        review.grades.append(Grade(name='Audience Score', value=float(grade_overall), best=100.0))

    summary = data.xpath('//div[@class="post"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/following-sibling::p[not(regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:") or preceding::h2[regexp:test(., "What |What’s ")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Bottom line")]]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion.strip(': '))

    excerpt = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/preceding-sibling::p[not((contains(., "Opening") and a) or regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not((regexp:test(., "Opening|The returning voice cast") and a) or regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
