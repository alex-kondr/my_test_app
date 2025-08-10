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
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://ausdroid.net/category/review/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h3/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[@aria-label="next-page"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace('Review Photo Gallery: ', '').replace('Ausdroid Reviews: ', '').replace('Ausdroid reviews: ', '').replace('Ausdroid reviews the ', '').replace('Australian Review of ', '').replace('Ausdroid Reviews ', '').replace('Ausdroid Reviews – ', '').split(' Review — ')[0].replace('Review — ', '').split(' Review – ')[0].replace('Review – ', '').split(' Review: ')[0].split(' review — ')[0].split(' review – ')[0].split(' review: ')[0].split(' review— ')[0].split(' review, ')[0].split(' — ')[0].replace(' – Australian Review', '').replace('Wireless chargers tested: ', '').replace('Weekend Warrior: ', '').replace('Hands On: ', '').replace('Review: ', '').replace('Review – ', '').replace(' – Review', '').replace(' Re-review', '').replace('Reviews: ', '').replace('Reviewed: ', '').replace(' Review', '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')

    product.category = data.xpath('//li[@class="entry-category" and not(regexp:test(., "News and Editorial|Reviews"))]/a/text()').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1[@class="entry-title"]//text()').string(multiple=True)
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "post-author-name")]/*[not(@class="td-author-by" or @class="td-author-line")]//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "post-author-name")]/*[not(@class="td-author-by" or @class="td-author-line")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "final-score")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.replace(',', '.'))
        if grade_overall > 5:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        else:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//tr[contains(@class, "review-row-stars")]')
    for grade in grades:
        grade_name = grade.xpath('td[contains(@class, "review-desc")]/text()').string()
        grade_val = grade.xpath('count(.//i[@class="td-icon-star"]) + count(.//i[@class="td-icon-star-half"]) div 2')

        if grade_name and grade_val > 0:
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    if not grades:
        grades = data.xpath('//tr[contains(@class, "review-row-bars")]')
        for grade in grades:
            grade_name = grade.xpath('.//div[contains(@class, "review-desc")]/text()').string()
            grade_val = grade.xpath('.//div[contains(@class, "review-percent")]/text()').string()

            if grade_name and grade_val:
                grade_val = float(grade_val.replace(',', '.'))
                if grade_val > 0:
                    review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    conclusion = data.xpath('//h2[contains(., "Conclusion")]/following-sibling::p[not(contains(., "You can purchase the "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h3|//p)[contains(., "Should you ")][last()]/following-sibling::p[not(contains(., "You can purchase the "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Closing thoughts")]/following-sibling::p[not(contains(., "You can purchase the "))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p[not(contains(., "You can purchase the ") or (contains(., "is available") and contains(., "website shop")))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h4[contains(., "Conclusion")]/following-sibling::p[not(contains(., "You can purchase the ") or (contains(., "is available") and contains(., "website shop")))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-summary-content")]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//h3|//p)[contains(., "Should you ")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "Closing thoughts")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h4[contains(., "Conclusion")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "post-content")]/p[not(contains(., "You can purchase the ") or (contains(., "is available") and contains(., "website shop")))]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
