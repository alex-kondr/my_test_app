from agent import *
from models.products import *
import re
import HTMLParser


h = HTMLParser.HTMLParser()


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


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
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('https://www.destructoid.com/reviews/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[contains(@class, "posts")]//a[.//h3]')
    for rev in revs:
        title = rev.xpath('.//h3/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '').replace('review-', '')
    product.category = 'Tech'

    name = data.xpath('//div[@class="verdict"]/strong/text()').string() or context['title']
    product.name = name.replace('Review – ', '').split(' – ')[0].split(' Review: ')[0].replace(' review', '').replace('Review: ', '').replace('Preview: ', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@class="post-modified"]/text()').string()
    if date:
        review.date = date.replace(' am', '').replace(' pm', '').strip(' |').rsplit(' ', 1)[0]

    author = data.xpath('//a[@class="author-name"]/text()').string()
    author_url = data.xpath('//a[@class="author-name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "score gree")]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[h4[contains(., "Pros")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[h4[contains(., "Cons")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//p[contains(@class, "post-summary")]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(h.unescape(summary)).replace(u'Å\x8d', u'ō').replace(u'Å\x81', u'ō').strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "overall", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="content-full"]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(h.unescape(conclusion)).replace(u'Å\x8d', u'ō').replace(u'Å\x81', u'ō').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "overall", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="post-content"]/p//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(h.unescape(excerpt)).replace(u'Å\x8d', u'ō').replace(u'Å\x81', u'ō').replace(u'â\x81\xa0', u'').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
