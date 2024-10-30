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
    session.queue(Request('https://www.delamar.de/testberichte/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//article[@class]/a|//article[@class]/p[@class="m-b-0"]/a')
    for rev in revs:
        title = rev.xpath('.//text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(' Testbericht', '').replace(' Test', '').replace('(open)', '').strip()
    product.ssid = context['url'].split('/')[-2].replace('-test', '')

    product.url = data.xpath('//a[contains(@class, "shop_button") or contains(., "Check Amazon") or contains(., "Check Thomann")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.category = data.xpath('//div[@class="row col-md-12 breadcrumbs"]//a[not(h1 or contains(., "Musiksoftware"))]/text()').string()
    if not product.category:
        product.category = 'Tech'

    manufacturer = data.xpath('//div[span[contains(., "Hersteller: ")]]//text()').string(multiple=True)
    if manufacturer:
        product.manufacturer = manufacturer.replace('Hersteller:', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//meta[@name="date"]/@content').string()

    author = data.xpath('//div[contains(@class, "author")]/div[contains(., "Von")]//text()').string(multiple=True)
    if author:
        author = author.split('am')[0].replace('Von', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[@class="rating_number"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    if not grade_overall:
        grade_overall = data.xpath('count(//span[@class="fa fa-star"]) + count(//span[contains(@class, "fa-star-half")]) div 2')
        if grade_overall:
            review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//ul[@class="pro"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="contra"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[@class="article_teaser"]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary)
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//div[contains(@class, "fazit")]/p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[regexp:test(., "fazit", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "verdict")]/p[@class="m-b-1"]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion)
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "fazit", "i")]/preceding-sibling::p[not(@class or audio or video)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="row"]/div/p[not(@class or audio or video)]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt)
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
