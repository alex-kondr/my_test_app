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
    session.queue(Request('https://camerastuffreview.com/lenzen/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[@class="elementor-post__title"]/a')
    for rev in revs:
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath('//a[@class="page-numbers next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2].replace('review-', '')
    product.category = 'Tech'

    title = data.xpath('//meta[@property="og:title"]/@content').string()
    product.name = title.replace('Full review: ', '').replace('Preview: ', '').replace('(P)review: ', '').replace('(P)review ', '').replace('Review: ', '').replace('REVIEW: ', '').replace('Full Review ', '').replace('Full review ', '').replace('Review ', '').replace(u'Review\u00a0', '').replace(' review', '').replace('Test: ', '').replace('TEST: ', '').replace('Test ', '').replace('TEST ', '').replace('test ', '').split(' – ')[0].split(' - ')[0].split(':')[0].strip()

    product.url = data.xpath('//a[@class="elementor-button elementor-button-link elementor-size-sm"]/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = title
    review.url = context['url']
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//td[contains(., "eindwaardering")]/following-sibling::td/text()').string()
    if grade_overall:
        grade_overall = grade_overall.replace(',', '.').strip(' +-–')
        try:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
        except:
            pass

    grades = data.xpath('//tr[td[1][regexp:test(., "^[\w/ ]+/\d+$") and not(.//h1 or .//h3)]]')
    for grade in grades:
        grade_name, grade_val = grade.xpath('td')
        grade_name, grade_best = grade_name.xpath('text()').string().rsplit('/', 1)
        grade_val = grade_val.xpath('text()').string()
        if grade_val and '*' in grade_val:
            grade_val = grade_val.count('*')
        elif grade_val:
            grade_val = grade_val.replace(',', '.').strip(' +-–')
        try:
            if float(grade_val) > float(grade_best):
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)+5))
            else:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=float(grade_best)))
        except:
            pass

    pros = data.xpath('//tr[contains(., "VOORDELEN")]/following-sibling::tr/td[1]//li')
    if not pros:
        pros = data.xpath('//h4[contains(., "Voordelen")]/following-sibling::ul[1]/li')
    for pro in pros:
        pro = remove_emoji(pro.xpath('.//text()').string(multiple=True).strip(' –'))
        if pro and len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//tr[contains(., "NADELEN") or contains(., "Nadelen")]/following-sibling::tr/td[2]//li')
    if not cons:
        cons = data.xpath('//h4[contains(., "Nadelen")]/following-sibling::ul[1]/li')
    for con in cons:
        con = remove_emoji(con.xpath('.//text()').string(multiple=True).strip(' –'))
        if con and len(con) > 1:
            review.add_property(type='cons', value=con)

    conclusions = data.xpath('//div[@data-id="12946e9" or @data-id="97121bd"]//p//text()[normalize-space()]').strings()
    if not conclusions:
        conclusions = data.xpath('(//tr[contains(., "Conclusie")]/following-sibling::tr/td/p[not(contains(., "insertgrid") or .//span[@class])]|//h3[contains(., "Conclusie")]/following::p[not(contains(., "insertgrid") or .//span[@class] or @class or contains(., "LAATSTE BERICHTEN FOCUS MAGAZINE"))])//text()[normalize-space()]').strings()
    if conclusions:
        conclusion = remove_emoji("".join(conclusions).strip())
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//h2|//h3)/following-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//table[@class="responsive"]//td[not(.//h1 or .//h3 or .//h4 or .//span[@class="titlereview"])]//text()[not(contains(., "insertgrid") or contains(., "{arimagnify"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="elementor-widget-container"]//p//text()').string(multiple=True)

    if excerpt:
        for conclusion in conclusions:
            excerpt = excerpt.replace(conclusion.strip(), '').strip()

        excerpt = remove_emoji((excerpt))

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
