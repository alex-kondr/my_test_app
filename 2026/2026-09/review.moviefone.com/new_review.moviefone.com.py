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
    session.queue(Request('https://www.moviefone.com/movies/reviews/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath('//a[contains(@class, "review-card-link")]')
    for rev in revs:
        title = rev.xpath('.//p[contains(@class, "review-excerpt")]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('movie-review', '').strip(' -')
    product.category = 'Movie'

    product.name = data.xpath('//a[contains(@class, "movie-card-titl")]/text()').string()
    if not product.name:
        product.name = context['title']

    genres = data.xpath('//a[contains(@class, "movie-card-genre")]/text()').join('/')
    if genres:
        product.category += '|' + genres

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@property="article:author"]/@content').string()
    author_url = data.xpath('//div[@class="article-byline-author"]/a/@href').string()
    if author and author_url and 'moviefone' not in author.lower():
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author and 'moviefone' not in author.lower():
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(span, "Review")]//span[@class="poster-score-num"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grade = data.xpath('//div[contains(span, "Audience")]//span[@class="poster-score-num"]/text()').string()
    if grade:
        review.grades.append(Grade(name='Audience', value=float(grade), best=100.0))

    summary = data.xpath('//p[@class="article-dek"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/following-sibling::p[not(regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:", "i") or preceding::h2[regexp:test(., "What |What’s ")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Bottom line")]]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion.strip(': '))

    excerpt = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/preceding-sibling::p[not((contains(., "Opening") and a) or regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:", "i"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "article-body")]/p[not((regexp:test(., "Opening|The returning voice cast") and a) or regexp:test(., "of 10 stars| out of 100| on Amazon|Buy Tickets:", "i"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)