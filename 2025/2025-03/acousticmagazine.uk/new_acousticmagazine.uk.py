from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://www.musicradar.com/reviews"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "listingResult small result") and .//h3[@class="article-name"]]')
    for rev in revs:
        title = rev.xpath('.//h3[@class="article-name"]//text()').string()
        cat = data.xpath('.//a[@class="category-link"]/text()').string()
        url = rev.xpath('.//a[@class="article-link"]/@href').string()
        session.queue(Request(url), process_review, dict(title=title, cat=cat, url=url))

    current_page = data.xpath('//span[@class="active"]/text()').string()
    page = context.get('page', 1)
    if current_page and current_page == str(page):
        next_url = "https://www.musicradar.com/reviews/page/" + str(page + 1)
        session.queue(Request(next_url), process_revlist, dict(page=page+1))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(':')[-1].replace(' review', '').replace('Review', '').strip()
    product.ssid = context['url'].split('/')[-1].replace('-review', '')
    product.category = context['cat']

    product.url = data.xpath('//a[@rel="sponsored noopener"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
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

    grade_overall = data.xpath('//div[contains(@class, "verdict")]//span/@aria-label').string()
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split('out')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[@class="pretty-verdict__pros"]/ul//p')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@class="pretty-verdict__cons"]/ul//p')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="header-sub-container"]/h2//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "review: Verdict")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(., "Sound On Sound"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="pretty-verdict__verdict"]/p//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('MuscRadar verdict:', '').replace('MusicRadar verdict:', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "review: Verdict")]/preceding-sibling::p[not(contains(., "MuscRadar verdict:") or contains(., "MusicRadar verdict:") or (.//strong[contains(., "MusicTech")] and .//a) or (.//strong[contains(., "Epicomposer")] and .//a))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p[not(contains(., "MuscRadar verdict:") or contains(., "MusicRadar verdict:") or (.//strong[contains(., "MusicTech")] and .//a) or (.//strong[contains(., "Epicomposer")] and .//a))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="article-body"]/p[not(contains(., "MuscRadar verdict:") or contains(., "MusicRadar verdict:") or (.//strong[contains(., "MusicTech")] and .//a) or (.//strong[contains(., "Epicomposer")] and .//a))]//text()').string(multiple=True)

    if excerpt:

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)