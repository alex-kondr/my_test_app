from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://gadgetsnow.indiatimes.com/reviews', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[a[@data-clink="y" and @class=""] and .//figcaption]')
    for rev in revs:
        title = rev.xpath('.//div[figcaption]/text()').string()
        brand = rev.xpath('.//div[figcaption]/div[not(contains(., "Reviews"))]/text()').string()
        url = rev.xpath('a/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, brand=brand, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review: ')[0].split(' Review: ')[0].replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.cms', '')
    product.category = 'Tech'
    product.manufacturer = context['brand']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[contains(@href, "/author/")]/text()').string()
    author_url = data.xpath('//a[contains(@href, "/author/")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('-')[-1].replace('.cms', '')
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(., "Critic Rating")]/span[@class]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//div[h4[contains(., "Pros")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h4[contains(., "Cons")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[h3[contains(., "Verdict")]]/div//span[not(regexp:test(., "Also read|\|"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//span|//strong)[regexp:test(., "Verdict|Conclusion")]/following-sibling::span//text()[not(regexp:test(., "Also read|\|"))]').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'Ã¢Â€Â™', "'").replace(u'ÃƒÂ¢Ã‚Â€Ã‚Â˜', "'").replace(u'ÃƒÂ¢Ã‚Â€Ã‚Â™', "'").replace(u'ÃƒÂ¢Ã‚Â€Ã‚Â', '').replace(u'Ã¢Â€Â�', '').replace(u'Ã¢Â€Âœ', '').replace(u'Ã¢Â€Âš', '').replace(u'Ã¢Â€Â', '').replace(u"''", "'")
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//span|//strong)[regexp:test(., "Verdict|Conclusion")]/preceding-sibling::span//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[@data-articlebody]/span|//div[@data-articlebody]/a|//div[@data-articlebody]//div[h3 and not(h3[contains(., "Verdict")])]/div)[not(contains(., "Read More"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'Ã¢Â€Â™', "'").replace(u'ÃƒÂ¢Ã‚Â€Ã‚Â˜', "'").replace(u'ÃƒÂ¢Ã‚Â€Ã‚Â™', "'").replace(u'ÃƒÂ¢Ã‚Â€Ã‚Â', '').replace(u'Ã¢Â€Â�', '').replace(u'Ã¢Â€Âœ', '').replace(u'Ã¢Â€Âš', '').replace(u'Ã¢Â€Â', '').replace(u"''", "'")
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
