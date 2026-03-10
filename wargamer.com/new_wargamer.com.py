from agent import *
from models.products import *
import simplejson


XCAT = ['About us']


def run(context, session):
    session.queue(Request('https://www.wargamer.com/', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul/li[contains(@class, "menu-item")]/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        cat_id = cat.xpath('@href').string().split('/')[-1]

        if name not in XCAT:
            url = 'https://www.wargamer.com/wp-json/ifs/v1/posts?per_page=60&page=1&category=' + cat_id
            session.queue(Request(url, max_age=0), process_revlist, dict(cat=name, cat_id=cat_id))


def process_revlist(data, context, session):
    revs = simplejson.loads(data.content)
    for rev in revs:
        title = rev.get('post_title')
        ssid = str(rev.get('ID'))
        url = rev.get('permalink')

        if 'review' in title.lower():
            session.queue(Request(url, max_age=0), process_review, dict(context, title=title, ssid=ssid, url=url))

    if len(revs) == 60:
        next_page = context.get('page', 1) + 1
        next_url = 'https://www.wargamer.com/wp-json/ifs/v1/posts?per_page=60&page={page}&category={cat}'.format(page=next_page, cat=context['cat_id'])
        session.queue(Request(next_url, max_age=0), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(" Review –")[0].split(' review –')[0].split(' review - ')[0].replace('review', '').replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="verdict-score"]//@src').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[-1].replace('.svg', '')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="pros"]//li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]//li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@id="article-details"]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Verdict", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Should you buy")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[@class="summary"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Verdict", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Should you buy")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(contains(., "for more news on"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
