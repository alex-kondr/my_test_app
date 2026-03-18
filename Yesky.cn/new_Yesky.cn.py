from agent import *
from models.products import *
import re


XCAT = ['peijian', 'gps', 'nctech', 'shouyou']   # 404


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('http://www.yesky.com/more/22_95575_pingce_1.shtml', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div/dl[@class="list"]/dd')
    for rev in revs:
        title = rev.xpath('h3/a/text()').string().replace('【视频】', '')
        url = rev.xpath('h3//a/@href').string()

        cat = url.split('://')[-1].split('.', 1)[0]
        if cat not in XCAT:
            session.queue(Request(url, max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//div[@class="pages"]/font/a[regexp:test(., "下一页", "i")]/@href').string()
    if next_url:
        session.queue(Request(next_url, max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = remove_emoji(context['title']).strip()
    product.url = context["url"]
    product.ssid = context["url"].split('/')[-1].split(".")[0]

    product.category = data.xpath('//div[@class="site"]//a[last()]/text()').string()
    if not product.category:
        product.category = data.xpath('//div[@class="current"]/a[not(contains(., "评测"))][last()]/text()').string()
    if not product.category:
        product.category = '技术'

    review = Review()
    review.title = context['title']
    review.url = product.url
    review.type = 'pro'
    review.ssid = product.ssid

    date = data.xpath('//span[@class="date"]/text()').string()
    if not date:
        date = data.xpath('//div[@class="detail" or @class="formwh"]/span[contains(., "-") or contains(., ". ")]/text()').string()

    if date:
        review.date = date.replace('. ', '-').split()[0]

    author = data.xpath('//span[contains(@class, "author")]/b/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="article_infor" or @class="article"]/p[not(.//a[contains(@href, "image")] or .//img[contains(@src, "image")])][not(contains(., "评测总评") or contains(., "写在最后") or contains(., "评测总结") or contains(., "【总结】"))][not(preceding-sibling::p[regexp:test(., "评测总结", "i") or regexp:test(., "评测总评", "i") or regexp:test(., "【总结】", "i") or regexp:test(., "写在最后", "i")])]//text()').string(multiple=True)
    if excerpt:
        context['excerpt'] = remove_emoji(excerpt).strip()

    next_url = data.xpath('//div[@class="pages"]/ul/li[a][1]/a/@href').string()
    if not next_url:
        next_url = data.xpath('//div[@class="pages"]/a[contains(., "下一页")]/@href').string()
    if not next_url:
        next_url = data.xpath('//a[@class="readall"][contains(@href, "all")]/@href').string()

    if next_url:
        if 'all.' in next_url:
            session.do(Request(next_url), process_review_next, dict(context, product=product, review=review))
            return

        title = data.xpath('//div[@class="pages"]/ul/li/span/text()').string()
        if not title:
            title = review.title + " - 页 1"

        review.add_property(type='pages', value=dict(title=title, url=review.url))
        session.do(Request(next_url), process_review_next, dict(context, product=product, review=review, page=2))

    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data, context, session)


def process_review_next(data, context, session):
    product = context['product']

    review = context['review']

    images = data.xpath("//div[@class='article_infor']//img")
    for image in images:
        image_src = image.xpath("@src").string()
        if image_src:
            product.add_property(type='image', value=dict(src=image_src, type='product'))

    grade_overall = data.xpath('//div[@class="article_infor"]/table//td[contains(., "★")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.count('★')
        if grade_overall and grade_overall > 0:
            review.grades.append(Grade(type="overall", value=float(grade_overall), best=5.0))

    conclusion = data.xpath('//p[*[self::span or self::strong][1][regexp:test(., "评测总结", "i") or regexp:test(., "评测总评", "i") or regexp:test(., "【总结】", "i") or regexp:test(., "写在最后", "i")]]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "【总结】")]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        if conclusion:
            review.add_property(type='conclusion', value=conclusion)

    page = context.get('page', 1)
    if page > 1:
        title = data.xpath('//div[@class="pages"]/ul/li/span/text()').string()
        if not title:
            title = review.title + " - 页 " + str(page)

        review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        excerpt = data.xpath('//div[@class="article_infor" or @class="article"]/p[not(.//a[contains(@href, "image")] or .//img[contains(@src, "image")])][not(contains(., "评测总评") or contains(., "写在最后") or contains(., "评测总结") or contains(., "【总结】"))][not(preceding-sibling::p[regexp:test(., "评测总结", "i") or regexp:test(., "评测总评", "i") or regexp:test(., "总结", "i") or regexp:test(., "写在最后", "i")])]//text()').string(multiple=True)
        if excerpt:
            if conclusion:
                excerpt = excerpt.replace(conclusion, '').strip()

            excerpt = remove_emoji(excerpt).strip()
            context['excerpt'] = context.get('excerpt', '') + " " + excerpt

    next_url = data.xpath('//div[@class="pages"]/ul/li[a][preceding-sibling::*[1][self::li[span]]]/a/@href').string()
    if not next_url:
        next_url = data.xpath('//div[@class="pages"]/a[contains(., "下一页")]/@href').string()

    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, page=page+1))

    elif context.get('excerpt'):
        review.add_property(type="excerpt", value=context['excerpt'].strip())

        product.reviews.append(review)

        session.emit(product)
