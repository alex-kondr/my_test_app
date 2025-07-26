from agent import *
from models.products import *
import re


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
    session.sessionbreakers = [SessionBreak(max_requests=6000)]
    session.queue(Request('https://www.journaldugeek.com/tests/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//main[@id="main"]/a')
    for rev in revs:
        title = rev.xpath('.//h2/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=remove_emoji(title), url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Test : ', '').split(' : ')[0].split(' : ')[0].replace('Test du ', '').replace('Test ', '').replace('Preview ', '').replace(' Preview', '').replace('[Test]', '').replace('[TEST]', '').strip()
    product.ssid = context['url'].split('/')[-2]
    product.category = data.xpath('//p[@class="post-tags"]/a[not(regexp:test(., "Test|preview|Home", "i"))]/text()').string() or 'Technologie'

    product.url = data.xpath('//a[contains(@href, "https://shop.journaldugeek.com/go")]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]/text()').string()
    author_url = data.xpath('//a[@rel="author"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[span[contains(text(), "Note :")]]/span[not(contains(., "Note"))]//text()').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//div[div/h3[contains(text(), "Les plus")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = remove_emoji(pro).strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[div/h3[contains(text(), "Les moins")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = remove_emoji(con).strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "post-excerpt")]/p//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[contains(., "Verdict")]/following-sibling::p[not(@class or preceding-sibling::h2[regexp:test(., "Prix")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[h2[contains(., "Notre avis")]]//div[@class="flex-1"]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(re.sub(r'\[nextpage title=”[^\[\]]+”\]', '', conclusion, flags=re.UNICODE)).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(@class or preceding-sibling::h2[regexp:test(., "Prix|Verdict")])]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(re.sub(r'\[nextpage title=”[^\[\]]+”\]', '', excerpt, flags=re.UNICODE)).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
