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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cliquenabend.de/spiele.html', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//td/a[b]')
    for rev in revs:
        title = rev.xpath('.//text()').string(multiple=True)
        url = rev.xpath('@href').string()
        session.queue(Request(url, force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[img[contains(@src, "arrow_right_green")]]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].replace(u'\uFEFF', '').replace('- Mini-Testspiel', '').replace(' Reviewers', '').strip()
    product.ssid = context['url'].split('/')[-1].split('-')[0]
    product.category = 'Spiele'
    product.manufacturer = data.xpath('//b[contains(., "Verlage:")]/following-sibling::ul[1]//a/text()').string()

    genres = data.xpath('//b[contains(., "Genres:")]/following-sibling::ul[1]//a/text()').join('/')
    if genres:
        product.category += '|' + genres

    product.url = data.xpath('//div[@class="bestellen"]//a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace(u'\uFEFF', '').strip()
    review.url = context['url']
    review.ssid = product.ssid

    author = data.xpath('//b[contains(., "Autoren:")]/following-sibling::ul[1]//a/text()').string()
    author_url = data.xpath('//b[contains(., "Autoren:")]/following-sibling::ul[1]//a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1].split('-')[0]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@id="ratingbox"]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0])
        review.grades.append(Grade(type='overall', value=grade_overall, best=10.0))

    grades = data.xpath('//table[@class="ratingtable"]//td//tbody/tr[.//img]')
    for grade in grades:
        grade_name = grade.xpath('td[@style]/text()').string(multiple=True)
        grade_val = float(grade.xpath('.//img/@alt').string().split()[0])
        description = grade.xpath('td[not(@style)]/text()').string(multiple=True)
        review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0, description=description))

    conclusion = data.xpath('//div[@id="part_wertungen"]//p//text()[not (contains(., "cliquenabend.de"))]').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    summary = data.xpath('//div[@id="rating_short_gesamt"]//text()').string()
    if summary and conclusion:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)
    elif summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='conclusion', value=summary)

    excerpt = data.xpath('//div[@id="part_test"]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
