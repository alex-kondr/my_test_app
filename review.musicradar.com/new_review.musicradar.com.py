from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.musicradar.com/reviews', use='curl', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//div[contains(@class, "subcategory-list")]/ul/li')
    for cat in cats:
        name = cat.xpath('h3//text()').string(multiple=True)
        url = cat.xpath('.//a/@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_revlist, dict(cat=name, cat_url=url))


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="article-link"]')
    for rev in revs:
        title = rev.xpath('@aria-label').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(context, title=title, url=url))

    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if current_page and int(current_page) == page:
        next_page = page + 1
        next_url = context['cat_url'] + '/page/{}'.format(next_page)
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(context, page=next_page))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(':')[-1].replace(' review', '').replace(' Review', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = context['cat'].replace(' Reviews', '').strip()

    product.url = data.xpath('//a[@rel="sponsored noopener"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[contains(@class, "review-title")]//text()').string(multiple=True)
    review.url = context['url']
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

    grade_overall = data.xpath('count(//div[contains(@class, "verdict")]//span[@class="icon icon-star"]) + count(//div[contains(@class, "verdict")]//span[@class="icon icon-star half"]) div 2')
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grades = data.xpath('//table[contains(., "Ratings")]/tbody/tr[not(contains(., "Overall"))]')
    for grade in grades:
        grade_name = grade.xpath('td[1]//text()').string(multiple=True)
        grade_desc = grade.xpath('td[2]//text()').string(multiple=True)
        grade_val = grade.xpath('td[3]//text()[contains(., "★")]').string(multiple=True).count('★')
        review.grades.append(Grade(name=grade_name, description=grade_desc, value=float(grade_val), best=5.0))

    pros = data.xpath('//div[@class="pretty-verdict__pros"]/ul//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.lstrip('…').strip(' +-•')
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pretty-verdict__cons"]/ul//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.lstrip('…').strip(' +-•')
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(., "Sound On Sound"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('MuscRadar verdict:', '').replace('MusicRadar verdict:', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Verdict")]/preceding-sibling::p[not(contains(., "★") or contains(., "MuscRadar verdict:") or contains(., "MusicRadar verdict:") or (.//strong[contains(., "MusicTech")] and .//a) or (.//strong[contains(., "Epicomposer")] and .//a))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(contains(., "★") or contains(., "MuscRadar verdict:") or contains(., "MusicRadar verdict:") or (.//strong[contains(., "MusicTech")] and .//a) or (.//strong[contains(., "Epicomposer")] and .//a))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(contains(., "★") or contains(., "MuscRadar verdict:") or contains(., "MusicRadar verdict:") or (.//strong[contains(., "MusicTech")] and .//a) or (.//strong[contains(., "Epicomposer")] and .//a) or preceding-sibling::h3[contains(., "The web says")])]//text()').string(multiple=True)

    if excerpt:

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
