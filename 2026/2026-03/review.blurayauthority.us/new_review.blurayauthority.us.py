from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.blurayauthority.com', use='curl', force_charset='utf-8', max_age=0), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//ul[@id="menu-main"]/li/a')
    for cat in cats:
        name = cat.xpath('span/text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="p-content"]/h3[@class="entry-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context))


def process_review(data, context, session):
    ssid = data.xpath('//article[contains(@class, "type-post")]/@id').string()
    if not ssid:
        return

    product = Product()
    product.name = context['title'].replace(u'Ã©', u'é').replace(u'Ã­', u'í').replace(u'Ã±', u'ñ').replace(u'Ã§', u'ç').replace(u'Ã ', u'à').replace(u'Ã¡', u'á').replace(u'Ã¯', u'ï').replace(u'Ã¶', u'ö').replace(u'Ã¼', u'ü').replace(u'Ã¥', u'å').replace(u'Ã¦', u'æ').replace(u'Â£', u'£').replace(u'Ã¢â‚¬â„¢', u"'").replace(u'Ã¢â‚¬â€œ', u'–').replace(u'Â', u' ').replace(u'\xa0', u' ').strip(u' +*,Â\xa0')
    product.url = context['url']
    product.ssid = ssid.split('-')[-1]
    product.category = context['cat']

    product.manufacturer = data.xpath('//span[contains(., "STUDIO")]/following-sibling::span[1]/text()').string()
    if not product.manufacturer:
        product.manufacturer = data.xpath('//span[contains(., "DIRECTOR")]/following-sibling::span[1]/text()').string()

    review = Review()
    review.title = context['title'].replace(u'Ã©', u'é').replace(u'Ã­', u'í').replace(u'Ã±', u'ñ').replace(u'Ã§', u'ç').replace(u'Ã ', u'à').replace(u'Ã¡', u'á').replace(u'Ã¯', u'ï').replace(u'Ã¶', u'ö').replace(u'Ã¼', u'ü').replace(u'Ã¥', u'å').replace(u'Ã¦', u'æ').replace(u'Â£', u'£').replace(u'Ã¢â‚¬â„¢', u"'").replace(u'Ã¢â‚¬â€œ', u'–').replace(u'Â', u' ').replace(u'\xa0', u' ').strip(u' +*,Â\xa0')
    review.url = product.url
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//p[contains(., "Review by:")]/span/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grades = data.xpath('//div[@class="review-content"]/div')
    for grade in grades:
        name = grade.xpath('.//span[@class="h3"]/text()').string()
        value = grade.xpath('.//img/@src').string()
        if name == 'OVERALL' and value:
            value = value.split('/')[-1].split('.')[0]
            review.grades.append(Grade(type='overall', value=float(value), best=100.0))
        elif name and value:
            value = value.split('/')[-1].split('.')[0]
            review.grades.append(Grade(name=name.title(), value=float(value), best=100.0))

    grade = data.xpath('//span[@class="tomatometercfresh"]/text()').string()
    if grade:
        grade = grade.strip(' %')
        if grade.isdigit() and float(grade) > 0:
            review.grades.append(Grade(name='Certified Fresh', value=float(grade), best=100.0))

    summary = data.xpath('//h2[contains(@class, "s-tagline")]/text()').string()
    if summary:
        summary = summary.replace(u'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œ', u'“').replace(u'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾\xa2', u'”').replace(u'Ã¢â‚¬â„¢', u"'").replace(u'Ã¢â‚¬â€œ', u'–').replace(u'Ã¢â‚¬Å“', u'“').replace(u'Ã¢â‚¬Â', u'”').replace(u'Ã¢â‚¬', u'—').replace('&eacut;', u'é').replace(u'Ã©', u'é').replace(u'Ã­', u'í').replace(u'Ã±', u'ñ').replace(u'Ã§', u'ç').replace(u'Ã ', u'à').replace(u'Ã¡', u'á').replace(u'Ã¯', u'ï').replace(u'Ã¶', u'ö').replace(u'Ã¼', u'ü').replace(u'Ã¥', u'å').replace(u'Ã¦', u'æ').replace(u'Â£', u'£').replace(u'Â', u' ').replace(u'\xa0', u' ').strip(u' +*,Â\xa0')
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//*[@id="the-bottom-line"]/following-sibling::p[not(contains(., "[Microsoft]"))]//text()[not(contains(., "[/") or contains(., "[fusion") or contains(., "dt_") or contains(., "[tweet") or contains(., "alert]") or contains(., "[youtube") or contains(., "quote]") or contains(., "[vc_") or contains(., "[history") or contains(., "[message"))]').string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œ', u'“').replace(u'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾\xa2', u'”').replace(u'Ã¢â‚¬â„¢', u"'").replace(u'Ã¢â‚¬â€œ', u'–').replace(u'Ã¢â‚¬Å“', u'“').replace(u'Ã¢â‚¬Â', u'”').replace(u'Ã¢â‚¬', u'—').replace('&eacut;', u'é').replace(u'Ã©', u'é').replace(u'Ã­', u'í').replace(u'Ã±', u'ñ').replace(u'Ã§', u'ç').replace(u'Ã ', u'à').replace(u'Ã¡', u'á').replace(u'Ã¯', u'ï').replace(u'Ã¶', u'ö').replace(u'Ã¼', u'ü').replace(u'Ã¥', u'å').replace(u'Ã¦', u'æ').replace(u'Â£', u'£').replace(u'Â', u' ').replace(u'\xa0', u' ').strip(u' +*,Â\xa0')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@itemprop="articleBody"]/p[not(contains(., "[Microsoft]"))][not(preceding-sibling::*[@id="the-bottom-line"])]//text()[not(contains(., "[/") or contains(., "[fusion") or contains(., "dt_") or contains(., "[tweet") or contains(., "alert]") or contains(., "[youtube") or contains(., "quote]") or contains(., "[vc_") or contains(., "[history") or contains(., "[message") or contains(., "[alert"))]').string(multiple=True)
    if excerpt:
        excerpt = excerpt.replace(u'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¹Ã…â€œ', u'“').replace(u'ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾\xa2', u'”').replace(u'Ã¢â‚¬â„¢', u"'").replace(u'Ã¢â‚¬â€œ', u'–').replace(u'Ã¢â‚¬Å“', u'“').replace(u'Ã¢â‚¬Â', u'”').replace(u'Ã¢â‚¬', u'—').replace('&eacut;', u'é').replace(u'Ã©', u'é').replace(u'Ã­', u'í').replace(u'Ã±', u'ñ').replace(u'Ã§', u'ç').replace(u'Ã ', u'à').replace(u'Ã¡', u'á').replace(u'Ã¯', u'ï').replace(u'Ã¶', u'ö').replace(u'Ã¼', u'ü').replace(u'Ã¥', u'å').replace(u'Ã¦', u'æ').replace(u'Â£', u'£').replace(u'Â', u' ').replace(u'\xa0', u' ').strip(u' +*,Â\xa0')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
