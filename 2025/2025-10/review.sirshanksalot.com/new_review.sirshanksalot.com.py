from agent import *
from models.products import *
import HTMLParser


h = HTMLParser.HTMLParser()


def run(context, session):
    session.queue(Request('https://sirshanksalot.com/', use='curl', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[a[contains(., "Reviews")]]/ul/li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name and url:
            name = name.replace('Reviews', '').strip()
            session.queue(Request(url, use='curl', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[contains(@property, "published_time")]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="author-name"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[regexp:test(., "– ?\d+ ?%") and (contains(., "Combined ") or regexp:test(., "Overall", "i") or regexp:test(., "Rating", "i"))]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.strip().split()[-1].split('%')[0])
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    grades = data.xpath('//p[regexp:test(., "– ?\d+ ?%") and not(contains(., "Combined ") or regexp:test(., "Overall Rating", "i")) and regexp:test(., "Rating", "i")]')
    for grade in grades:
        grade_name, grade_value = grade.xpath('.//text()').string(multiple=True).split('–')
        grade_name = grade_name.replace('Overall', '').replace('Rating', '').strip()
        grade_value = float(grade_value.replace('%', '').strip())
        if grade_name and grade_value:
            review.grades.append(Grade(name=grade_name, value=grade_value, best=100.0))

    conclusion = data.xpath('(//div[@itemprop="text"]/div|//div[@itemprop="text"]//p)[regexp:test(., "^Conclusion", "i")]/following-sibling::*[not((contains(., "Overall ") and contains(., " Rating")) or regexp:test(., "On eBay", "i") or regexp:test(., "On faceboo", "i") or contains(., "Titleist Links") or regexp:test(., "^Links:"))][not(preceding-sibling::*[contains(., "Titleist Links") or regexp:test(., "^Links:")])][not(regexp:test(., "–\s*\$\d"))]//text()').string(multiple=True)
    if conclusion and conclusion.strip():
        conclusion = h.unescape(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//div[@itemprop="text"]/div|//div[@itemprop="text"]//p)[not(regexp:test(., "–\s*\$\d") or (contains(., "Overall ") and contains(., " Rating")) or regexp:test(., "On eBay", "i") or regexp:test(., "On faceboo", "i") or contains(., "Titleist Links") or regexp:test(., "^Links:"))][not(preceding-sibling::*[contains(., "Titleist Links") or regexp:test(., "^Links:")])]//text()').string(multiple=True)
    if excerpt and excerpt.strip():
        excerpt = h.unescape(excerpt).replace('ï¿½', '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
