from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.theverge.com/reviews/', use='curl', force_charset='utf-8', max_age=0), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//ul/li//a[contains(., " Reviews") and not(contains(., "All Reviews"))]')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//a[contains(@class, "comments-link")]')
    for rev in revs:
        url = rev.xpath('@href').string().split('#')[0]
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    title = data.xpath('//div[@class=""]/h1//text()').string(multiple=True)
    if not title:
        return

    product = Product()
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat'].replace(' Reviews', '').strip()

    name = data.xpath('//div/h3[not(@data-native-ad-id)]//a//text()[not(regexp:test(., "on creating|director "))]').string(multiple=True)
    if not name:
        name = title

    product.name = name.split(' review:')[0].split(' tests: ')[0].split(' test: ')[0].split(' preview: ')[0].split('Review:')[-1].replace('(as reviewed)', '').replace('as reviewed:', '').replace('Read our full review of', '').replace('Read our review of', '').replace(' review', '').replace(' Review', '').strip().capitalize()

    product.url = data.xpath('//div/h3[not(@data-native-ad-id)]//a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "https://www.theverge.com/authors/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "https://www.theverge.com/authors/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "scorecard ")]/div/div[p[contains(., "Verge Score")]]/p[not(contains(., "Verge Score"))]//text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//h4[contains(., "The Good")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//h4[contains(., "The Bad")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class=""]/p[contains(@class, "dangerously")]//text()').string(multiple=True)
    if summary:
        summary = summary.replace(u'\uFEFF', '').strip()
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[contains(@class, "body-component")]/p[not(.//em[regexp:test(., "Photography by|Update, ")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
