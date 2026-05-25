from agent import *
from models.products import *
import re
import time
import random


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
    session.queue(Request('https://xboxlive.fr/tag/test/'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//article[contains(@class, "type-post")]')
    for rev in revs:
        title = rev.xpath('.//h2[@class="entry-title"]/a/span/text()').string()
        url = rev.xpath('.//h2[@class="entry-title"]/a/@href').string()
        ssid = rev.xpath('@id').string()
        session.queue(Request(url), process_product, dict(title=title, url=url, ssid=ssid))

    next_url = data.xpath('//div[@class="nav-previous"]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_product(data, context, session):
    strip_namespace(data)

    time.sleep(random.uniform(1, 3))

    product = Product()
    product.ssid = context['ssid'].replace('post-', '')
    product.category = 'Games'

    product.name = data.xpath('//div[contains(@class, "wp-block-copilot")]/h2/text()').string()
    if not product.name:
        product.name = context['title'].replace('[TEST]', '').replace('[Test] ', '').strip()

    product.url = data.xpath('//p[regexp:test(., "Acheter sur le", "i")]/a/@href | //a[regexp:test(., "Acheter sur le", "i")]/@href').string()
    if not product.url:
        product.url = context['url']

    manufacturer = data.xpath('//div[contains(@class, "wp-block-copilot")]//p[regexp:test(., "Développeur\s*:") or regexp:test(., "Developer\s*:") or regexp:test(., "Publisher\s*:")]//text()[normalize-space()]').string()
    if not manufacturer:
        manufacturer = data.xpath('//p//em/text()[contains(., "Développeur")]').string()

    if manufacturer:
        product.manufacturer = manufacturer.split(': ', 1)[-1].strip()

    platforms = data.xpath('//div[contains(@class, "wp-block-copilot")]//p/font[contains(., "Platforms:")]/text()').string()
    if not platforms:
        platforms = data.xpath('//p//em/text()[contains(., "Plateformes")]').string()
    if not platforms:
        platforms = data.xpath('//p//text()[contains(., "Plateformes")]').string()

    if platforms:
        product.category += '|' + platforms.split(': ')[-1].replace(' / ', '\\').replace('/', '\\').replace(' et ', ', ').replace(', ', '/')

    images = data.xpath("//div[@class='entry-content']//iframe/@data-placeholder-image | //img[contains(@class, 'attachment-full')]/@src").strings()
    for src in images:
        product.add_property(type="image", value={'src': src})

    review = Review()
    review.type = "pro"
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//time[contains(@class, "published")]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[contains(@class, "author")]/a//text()').string(multiple=True)
    author_url = data.xpath('//span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.strip('/').split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "wp-block-copilot")]//div[contains(text(), "%")]/text()').string()
    if grade_overall:
        grade_overall = grade_overall.strip('% ')
        if grade_overall and grade_overall[0].isdigit() and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    grades = data.xpath('//div[contains(@class, "wp-block-copilot")]//label[contains(., "(") and contains(., "/") and contains(., ")")]')
    for grade in grades:
        grade = grade.xpath('.//text()').string(multiple=True)
        grade_name = grade.rsplit(' (')[0]
        grade_values = grade.rsplit(' (')[-1].strip(') ')
        if grade_name and grade_values:
            grade_value, grade_best = grade_values.split('/')
            review.grades.append(Grade(name=grade_name, value=float(grade_value), best=float(grade_best)))

    pros = data.xpath('//div[*[self::h2 or self::h3][regexp:test(., "Positives", "i") or regexp:test(., "Positifs", "i")]]/ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip('+*-_—, ')
            if len(pro) > 1:
                review.add_property(type="pros", value=pro)

    cons = data.xpath('//div[*[self::h2 or self::h3][regexp:test(., "Negatives", "i") or regexp:test(., "Négatifs", "i")]]/ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip('+*-_—, ')
            if len(con) > 1:
                review.add_property(type="cons", value=con)

    conclusion = data.xpath('//div[@class="entry-content"]//p[preceding-sibling::*[self::h2 or self::h3][regexp:test(., "Conclusion")]][not(contains(., "Testé sur") or contains(., "Date de sortie") or contains(., "Acheter sur le"))]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        if conclusion:
            review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="entry-content"]//p[not(preceding::*[self::h2 or self::h3][regexp:test(., "Conclusion")])][not(contains(., "Testé sur") or contains(., "Date de sortie") or contains(., "Acheter sur le"))]//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        if len(excerpt) > 2:
            review.add_property(type="excerpt", value=excerpt)

            product.reviews.append(review)

            session.emit(product)
