from agent import *
from models.products import *


OPTIONS = """--compressed -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: XSRF-TOKEN=eyJpdiI6IlNIUlNJblwvREMzaktWWm9nT1RPVlV3PT0iLCJ2YWx1ZSI6IjUrcGxSOU4xMmtVeUdFeFJpVzBKRUxhcmJcL1J4UFZ6VWw3QXhGT292RWxhQ2t5cFZPWnpnVlNZR2pKbmd0WmdEIiwibWFjIjoiMmExZDg2ZDcwYmY3MGJiYzRlODQzZTkyOGJkMGY1NmM0ZDc3NTQwY2RmNzQxODU5MTk0MTgzODEwZTFmYTFjYiJ9; moviefone_session=eyJpdiI6ImcrQ2YrWHg2WnptVFZhdG5OcmxxRnc9PSIsInZhbHVlIjoiQzcrbW1Udk9URzNXRmZYWldqWEwxMmp3d0t5NVI3UURMZUVqRGxnYklqcHNLU003K01XMW1HNkh6UURNbXFVMCIsIm1hYyI6ImY2MTRlNmViYTFhOWYzODA4OTZjY2JmMzJkODUyYTA2NTBkODdlNWZkNjhjODMwODVjYTNjNjU0ZDlkOWY1NzEifQ%3D%3D' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' -H 'Priority: u=0, i' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache'"""


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
    session.queue(Request('https://www.moviefone.com/movies/reviews/', use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, {})


def process_revlist(data, context, session):
    strip_namespace(data)
    
    data.xpath('/').pretty()
    

    revs = data.xpath('//div[@class="mf-movie-review" and not(.//h2/a[contains(@href, "/main/")])]')
    for rev in revs:
        title = rev.xpath('.//h2/a/strong/text()').string()
        url = rev.xpath('.//h2/a/@href').string()
        grade_overall = rev.xpath('.//div[@class="score-bar-bar"]/text()').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_review, dict(title=title, grade_overall=grade_overall, url=url))

    next_url = data.xpath('//a[@class="next-button"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0, options=OPTIONS), process_revlist, {})


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split('Movie Review')[0].strip(" '‘’")
    product.url = data.xpath('//a[contains(@class, "info-title")]/@href').string() or context['url']
    product.ssid = data.xpath('//article[contains(@id, "article-")]/@id').string().split('-')[-1]
    product.category = 'Movie'

    genres = data.xpath('//a[contains(@class, "genre")]/text()').join('/')
    if genres:
        product.category += '|' + genres

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

    grade_user = context.get('grade')
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
