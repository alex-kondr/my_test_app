from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.queue(Request("https://live-soundguys.pantheonsite.io/wp-json/api/pages/reviews/?page=1&per_page=12&ts=1757325656635", use='curl', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs_json = simplejson.loads(data.content)
    if not revs_json:
        return

    revs = revs_json.get('data', {}).get('content', {}).get('posts', [])
    for rev in revs:
        title = rev.get('title')
        ssid = str(rev.get('ID'))
        cat = rev.get('topic')
        author = rev.get('author_name')
        author_ssid = rev.get('author_slug')
        url = "https://www.soundguys.com/" + rev.get('slug') + "/"
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(title=title, ssid=ssid, cat=cat, author=author, author_ssid=author_ssid, url=url))

    next_page = context.get('page', 1) + 1
    page_cnt = revs_json.get('data', {}).get('content', {}).get('total_pages', 0)
    if next_page <= page_cnt:
        next_url = "https://live-soundguys.pantheonsite.io/wp-json/api/pages/reviews/?page={}&per_page=12&ts=1757325656635".format(next_page)
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' review', '').replace(' Review', '').replace(' - Which are right for you?', '').strip()
    product.ssid = context['ssid']
    product.category = context['cat'] or 'Sound'

    product.url = data.xpath('//div[div/span[contains(text(), "Amazon")]]/a/@href').string()
    if not product.url:
        product.url = context['url']

    prod_json = data.xpath('//script[@type="application/json"]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json).get('props', {}).get('pageProps', {}).get('page', {}).get('productBars')
        if prod_json:
            product.manufacturer = prod_json[0].get('brand')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    if context['author'] and context['author_ssid']:
        author_url = 'https://www.soundguys.com/author/{}/'.format(context['author_ssid'])
        review.authors.append(Person(name=context['author'], ssid=context['author_ssid'], profile_url=author_url))

    grade_overall = data.xpath('//div[contains(@style, "--gradid:url")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//div[div[contains(text(), "Rating Metric")]]/div[contains(@class, "Oi")]')
    for grade in grades:
        grade_name = grade.xpath('text()').string()
        grade_val = grade.xpath('following-sibling::div[1][contains(@class, "Pi")]/text()').string()
        review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    pros = data.xpath('//div[div[contains(text(), "What we like")]]/div[not(contains(text(), "What we like"))]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('<br>', '').strip(' +-*.')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('''//div[div[contains(text(), "What we don't like")]]/div[not(contains(text(), "What we don't like"))]''')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('<br>', '').strip(' +-*.')
        if len(con) > 1:
            review.add_property(type="cons", value=con)

    summary = data.xpath('//div[h1]/div//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//div[h2[contains(., "What should you get")]]/following-sibling::div/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="e_Jh"]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[h2[contains(., "What should you get")]]/preceding-sibling::div/p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@data-content-wrapper="true"]/div/p//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
