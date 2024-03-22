from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.neowin.net/news/tags/review'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[@class="news-item-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    revs_cnt = data.xpath('count(//h3[@class="news-item-title"]/a)')
    if revs_cnt == 40:
        next_page = context.get('page', 1) + 1
        session.queue(Request('http://www.neowin.net/news/tags/review?page=' + str(next_page)), process_revlist, dict(page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Review:', '').split(':')[0].replace('review', '').replace('Review', '').replace('[Update]', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Tech'

    product.url = data.xpath('//h3/a[@rel="sponsored"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//p[@class="article-meta"]//time/@datetime').string()
    if date:
        review.date = ' '.join(date.split()[0:3])

    author = data.xpath('//p[@class="article-meta"]//a[@rel="author"]/text()').string()
    author_url = data.xpath('//p[@class="article-meta"]//a[@rel="author"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@class="rating"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[@class="pros"]/div[@class="small"]/text()').string(normalize_space=False)
    if pros:
        pros = pros.split('\n')
        for pro in pros:
            pro = pro.replace('•', '').replace('- ', '').replace('+ ', '').replace('-...', '').replace('...', '').strip()
            if pro.startswith('-'):
                pro = pro[1:]

            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="cons"]/div[@class="small"]/text()').string(normalize_space=False)
    if cons:
        cons = cons.split('\n')
        for con in cons:
            con = con.replace('•', '').replace('- ', '').replace('+ ', '').replace('-...', '').replace('...', '').strip()
            if con.startswith('-'):
                con = con[1:]

            review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h1[contains(., "Conclusion")]/following-sibling::p[not(@class or @style)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(@class or @style)]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p[not(@class or @style)]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h1[contains(., "Conclusion")]/preceding-sibling::p[not(@class or @style)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(@class or @style)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p[not(@class or @style)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]//p[not(@class or @style)]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
