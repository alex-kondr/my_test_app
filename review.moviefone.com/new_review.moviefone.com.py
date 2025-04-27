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
    session.queue(Request('https://www.moviefone.com/movie-reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="mf-movie-review" and not(.//h2/a[contains(@href, "/main/")])]')
    for rev in revs:
        title = rev.xpath('.//h2/a/text()').string()
        url = rev.xpath('.//h2/a/@href').string()
        grade_overall = rev.xpath('.//div/@data-score').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, grade_overall=grade_overall, url=url))

    next_url = data.xpath('//a[@class="next-button"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, {})


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('Movie Review')[0].strip(" '‘’")
    product.url = data.xpath('//a[@class="movie-info-showtimes"]/@href').string() or context['url']
    product.ssid = data.xpath('//article[contains(@id, "article-")]/@id').string().split('-')[-1]
    product.category = 'Movie'

    review = Review()
    review.title = data.xpath('//h1[@class="article-title"]/text()').string()
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'
    review.date = data.xpath('//a[@class="articlehead-date"]/text()').string()

    author = data.xpath('//a[@class="article-author-name"]/text()').string()
    author_url = data.xpath('//a[@class="article-author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url = author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = context.get('grade')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    if not grade_overall:
        grade_overall = data.xpath('//p[contains(., "of 10 stars")]//text()').string(multiple=True)
        if grade_overall:
            grade_overall = grade_overall.split('receives')[-1].split()[0]
            if grade_overall:
                review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//p[@class="article-tagline"]/text()').string(multiple=True)
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "final thoughts", "i")]/following-sibling::p[not(preceding-sibling::p[contains(., "of 10 stars")] or contains(., "of 10 stars"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Bottom line")]]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type="conclusion", value=conclusion.strip(': '))

    excerpt = data.xpath('//div[@class="post-content"]/p[not(preceding-sibling::h2[regexp:test(., "final thoughts", "i")])][not(self::p[strong[contains(., "Bottom line")]])][not(regexp:test(., " stars", "i") and regexp:test(., " out o", "i"))][not(preceding-sibling::p[strong[contains(., "Bottom line")]])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
