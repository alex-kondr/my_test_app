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
    session.queue(Request('https://www.all-nintendo.com/category/tests/', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//h2[@class="post-title"]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.url = context['url']

    product.name = context['title'].split(' - ')[0].split(' – ')[0].split('Test :')[-1].split('test :')[-1].split('test:')[-1].split(": ")[0].replace('Test ', '').replace('et tout le tra la la en test', '').strip()
    if len(product.name) < 3:
        product.name = context['title'].replace('Test :', '').replace('Test ', '').strip()

    prod_ssid = re.search(r"\d+/$", product.url)
    if prod_ssid:
        product.ssid = prod_ssid.group().strip('/')
    else:
        product.ssid = product.url.split('/')[-2].replace('-test-sur', '')

    category = context['title'].split('Test sur')[-1].split('test sur')[-1].split('Preview sur')[-1].split(' – Test ')[-1].split(': Test')[-1].split(' – ')[-1].split('Le Test')[-1].replace('Test complet de la', '').replace('(version alpha)', '').strip()
    if len(category) > 1 and 'test' not in category.lower() and '!' not in category:
        product.category = 'Games|' + category
    else:
        product.category = 'Games'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="entry-meta"]//time[contains(@class, "published")]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="entry-meta"]//a[contains(@class, "author_name")]/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[regexp:test(normalize-space(.), "\d+/\d+$") and contains(., "Globale")]//text()').string()
    if not grade_overall:
        grade_overall = data.xpath('//p[regexp:test(normalize-space(.), "\d+/\d+$")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.split(':')[-1].split(' ')[-1].split('/')[0].replace(',', '.')
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=20.0))

    grades = data.xpath('//p[regexp:test(normalize-space(.), "\d+/\d+$") and not(contains(., "Globale"))]')
    for grade in grades:
        grade = grade.xpath('.//text()').string(multiple=True)
        if ':' in grade:
            grade_name = grade.split(':')[0].strip()
            grade_val = grade.split(':')[-1].split('/')[0].replace(',', '.').strip()
        else:
            grade_name = grade.split(' ')[0].strip()
            grade_val = grade.split(' ')[-1].split('/')[0].replace(',', '.').strip()

        if len(grade_name) > 1 and 'note' not in grade_name.lower() and grade_val.isdigit():
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=20.0))

    pros = data.xpath('//p[contains(., "Les trucs cools du Jeu")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).strip(' +-*\n–')
        if len(pro) > 1:
            review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//p[.//strong[regexp:test(normalize-space(.), "^\+$")]]/following-sibling::p[regexp:test(normalize-space(.), "^–|^-") and not(preceding-sibling::p[regexp:test(normalize-space(.), "^–$")])]//text()').string(multiple=True)
        if pros:
            pros = pros.split('-')
            if len(pros) == 1:
                pros = pros[0].split('–')

            for pro in pros:
                pro = pro.strip(' +-*\n–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[contains(., "Les petits bémols")]/following-sibling::ul[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).strip(' +-*\n–')
        if len(con) > 1:
            review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//p[.//strong[regexp:test(normalize-space(.), "^–$")]]/following-sibling::p[regexp:test(normalize-space(.), "^–|^-")]//text()').string(multiple=True)
        if cons:
            cons = cons.split('-')
            if len(cons) == 1:
                cons = cons[0].split('–')
            for con in cons:
                con = con.strip(' +-*\n–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[regexp:test(., "conclusion", "i")]/following-sibling::p[not(contains(., "Note") or .//strong[regexp:test(normalize-space(.), "\d+/\d+|^\+$|^–|^-$")] or regexp:test(normalize-space(.), "^–|^-"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[regexp:test(., "Bilan|Conclusion")]/following-sibling::p[not(contains(., "Note") or .//strong[regexp:test(normalize-space(.), "\d+/\d+|^\+$|^–|^-$")] or regexp:test(normalize-space(.), "^–|^-"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[regexp:test(., "Bilan|Conclusion")]//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).replace('Bilan :', '').replace('Bilan:', '').replace('Conclusion :', '').replace('Conclusion:', '').replace('Bilan', '').replace('Conclusion','').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2[regexp:test(., "conclusion", "i")])[1]/preceding-sibling::p[not(contains(., "Les trucs cools du Jeu") or contains(., "Les petits bémols") or contains(., "Q :") or contains(., "Note") or .//strong[regexp:test(normalize-space(.), "\d+/\d+|^\+$|^–|^-$")] or regexp:test(normalize-space(.), "^–|^-"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p[regexp:test(., "Bilan|Conclusion")])[1]/preceding-sibling::p[not(contains(., "Note") or .//strong[regexp:test(normalize-space(.), "\d+/\d+|^\+$|^–|^-$")] or regexp:test(normalize-space(.), "^–|^-"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]//p[not(contains(., "Les trucs cools du Jeu") or contains(., "Les petits bémols") or contains(., "Q :") or contains(., "Note") or .//strong[regexp:test(normalize-space(.), "\d+/\d+|^\+$|^–|^-$")] or regexp:test(normalize-space(.), "^–|^-"))]//text()').string(multiple=True)

    if excerpt:

        if conclusion:
            excerpt = remove_emoji(excerpt).replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
