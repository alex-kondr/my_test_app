from agent import *
from models.products import *
import re


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
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://www.delamar.de/testberichte/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//a[@class="stretched-link"]')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Testbericht', '').replace(' BlindTest', '').replace(' Test', '').replace('(open)', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-test', '')
    product.manufacturer = data.xpath('//li[contains(., "Hersteller: ")]/a/text()').string(multiple=True)

    product.url = data.xpath('//a[contains(@class, "shop_button") or regexp:test(., "Check Amazon|Check Thomann", "i")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('(//ul[li[contains(., "Hersteller: ")]]/li)[2]/text()').string()
    if not product.category or not product.manufacturer:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//p[img[contains(@src, "/authors/")]]/text()').string(multiple=True)
    if date:
        review.date = date.split(' am ')[-1]

    author = data.xpath('//p[img[contains(@src, "/authors/")]]/img/@title').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[p[contains(., "SCORE")]]/p[not(contains(., "SCORE"))]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//ul[contains(@class, "ul_pro")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-—*.')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[contains(@class, "ul_contra ")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-—*.')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[contains(@class, "h1")]/span/text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "fazit")]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[not(.//p[contains(., "SCORE")] or contains(@class, "fazit"))]/p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
