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
    session.queue(Request('https://www.moviefone.com/movies/reviews/'), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="mf-movie-review" and not(.//h2/a[contains(@href, "/main/")])]')
    for rev in revs:
        title = rev.xpath('.//h2/a/strong/text()').string()
        url = rev.xpath('.//h2/a/@href').string()
        grade_user = rev.xpath('.//div[@class="score-bar-bar"]/text()').string()
        session.queue(Request(url), process_review, dict(title=title, grade_user=grade_user, url=url))

    next_url = data.xpath('//a[@class="next-button"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, {})


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('Movie Review')[0].strip(" '‘’")
    product.url = data.xpath('//a[contains(@class, "info-title")]/@href').string() or context['url']
    product.ssid = data.xpath('//article[contains(@id, "article-")]/@id').string().split('-')[-1]
    product.category = 'Movie'

    review = Review()
    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath('//a[@class="articlehead-date"]/text()').string()

    author = data.xpath('//a[contains(@class, "author-name")]/text()').string()
    author_url = data.xpath('//a[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url = author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "rating-score") and div[@class="score-text"]]/@data-score').string()
    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., " out of 100")]//text()').string(multiple=True)

    if grade_overall:
        grade_overall = grade_overall.split('score of ')[-1].split(' out of ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., "of 10 stars")]//text()').string(multiple=True)
        if grade_overall:
            grade_overall = grade_overall.split('receives a ')[-1].split('receives ')[-1].split(' out of ')[0]
            if grade_overall:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grade_user = context.get('grade_user')
    if grade_user:
        review.grades.append(Grade(name='Audience Score', value=float(grade_user), best=100.0))

    summary = data.xpath('//p[contains(@class, "article-tagline")]/text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/following-sibling::p[not(regexp:test(., "of 10 stars| out of 100"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Bottom line")]]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion.strip(': '))

    excerpt = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/preceding-sibling::p[not((contains(., "Opening") and a) or regexp:test(., "of 10 stars| out of 100"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not((regexp:test(., "Opening|The returning voice cast") and a) or regexp:test(., "of 10 stars| out of 100"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
