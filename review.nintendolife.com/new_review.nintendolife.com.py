from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.nintendolife.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "title")]')
    for rev in revs:
        title = rev.xpath('span[contains(@class, "title")]/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//div[contains(., "Title")]/p[@class="definition"]//text()').string().replace(u'\uFEFF', '').strip()
    product.ssid = context['url'].split('/')[-1]
    product.manufacturer = data.xpath('//div[contains(., "Developer")]/p[@class="definition"]//text()').string()

    product.url = data.xpath('//div[contains(., "Official Site")]/p[@class="definition"]/a/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = 'Games'
    platforme = data.xpath('//div[contains(., "System")]/p[@class="definition"]//text()').string()
    if platforme:
        product.category += '|' + platforme.replace(' eShop', '')

    genres = data.xpath('//div[contains(., "Genre")]/p[@class="definition"]/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'\uFEFF', '').strip()
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//ul[@class="article-author"]//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//ul[@class="article-author"]//a[@class="author-name"]/text()').string()
    author_url = data.xpath('//ul[@class="article-author"]//a[@class="author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="value accent"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grade = data.xpath('//div[@class="user-rating"]//span[@class="score accent" and not(contains(., "N/A"))]/text()').string()
    if grade:
        review.grades.append(Grade(name="Game Rating", value=float(grade), best=10.0))

    pros = data.xpath('//ul[@class="positives"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.replace(u'\uFEFF', '').strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="negatives"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.replace(u'\uFEFF', '').strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="content"]/p[@class="description"]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(@class)]//text()').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "body")]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
