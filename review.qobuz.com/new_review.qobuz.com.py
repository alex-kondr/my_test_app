from agent import *
from models.products import *
import re


XCAT = ['A Propos', 'La Rédaction', 'Le blog Qobuz', 'NEWS']


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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.browser.use_new_parser = True
    session.queue(Request('https://www.qobuz.com/fr-fr/magazine'), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//div[@class="col-03"]/nav/nav/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))

    cats = data.xpath('//div[@class="col-03"]/nav/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()

        if name not in XCAT:
            session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="section-cards-element"]')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('.//a[@class=""]/@href').string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@class="store-paginator__button next "]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h1[@class="magazine-header-title"]/text()').string()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url
    review.date = data.xpath('//time/@datetime').string()

    author = data.xpath('//div[@class="magazine-header-author"]/a/text()').string()
    author_url = data.xpath('//div[@class="magazine-header-author"]/a/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//div[@class="pros-container"]/span')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[contains(@class, "cons-container")]/span')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    summary = data.xpath('//section[@class="story-row story-desc"]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary)
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[@class="features-value"]//text()').string(multiple=True)
    conclusions = data.xpath('//div[@class="story-row story-body" and not(contains(., "Facebook"))]//p[contains(., "Conclusion :")]')
    if not conclusion:
        conclusion = data.xpath('//div[@class="story-row story-body" and not(contains(., "Facebook"))]//p[b[contains(., "Conclusion")]]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion)
        review.add_property(type='conclusion', value=conclusion)
    elif conclusions:
        conclusions = [concl.xpath('.//text()').string(multiple=True) for concl in conclusions]
        conclusion = remove_emoji(' '.join(conclusions).replace('Conclusion', '').strip())
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="story-row story-body" and not(contains(., "Facebook") or .//span[contains(@class, "hl")] or contains(., "Prix :") or contains(., "Amplification :") or contains(., "Connectivité :") or contains(., "Streaming :"))]//p[not(@class)]//text()').string(multiple=True)
    if excerpt:
        for concl in conclusions:
            excerpt = excerpt.replace(concl, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = remove_emoji(excerpt)
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
