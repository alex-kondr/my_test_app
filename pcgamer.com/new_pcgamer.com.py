from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://www.pcgamer.com/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat='Games|PC'))
    session.queue(Request('https://www.pcgamer.com/hardware/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat='Hardware'))


def process_revlist(data, context, session):
    page = context.get('page', 1)
    current_page = data.xpath('//div[@class="flexi-pagination"]//span[@class="active"]/text()').string()
    if not current_page or int(current_page) != page:
        return

    revs = data.xpath('//div[contains(@class, "review")]/div[contains(@class, "listingResult small result")]')
    for rev in revs:
        title = rev.xpath('.//h3[@class="article-name"]//text()').string()
        url = rev.xpath('.//a[@class="article-link"]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = 'https://www.pcgamer.com/reviews/page/{}/'.format(page+1)
    session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, page=page+1))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' review', '').split(' Review')[0].strip()
    product.ssid = context['url'].split('/')[-2].replace('-review', '')
    product.category = context['cat']
    product.manufacturer = data.xpath('(//strong[contains(., "Developer")]/following-sibling::text())[1]').string()

    product.url = data.xpath('//a[regexp:test(., "Check Amazon")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(., "Official site")]/@href').string()
    if not product.url:
        product.url = data.xpath('//strong[contains(., "Link")]/following-sibling::a[1]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content|//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="score score-long"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    pros = data.xpath('//div[h4[contains(., "For")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h4[contains(., "Against")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[@class="game-verdict"]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
