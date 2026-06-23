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
    session.queue(Request('https://www.pcquest.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    strip_namespace(data)

    revs = data.xpath('//div[@class="small-post"]/a[div[contains(@class, "title")]]')
    for rev in revs:
        title = rev.xpath('div/text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review: ')[0].split(' review: ')[0].replace('Gaming- Review', '').replace('Review:', '').replace(':Review', '').replace('Review of', '').replace(' Review', '').replace('review: ', '').replace('review-', '').replace(' review', '').replace(' REVIEW', '').strip()
    product.url = context['url']

    product.ssid = product.url.split('-')[-1].replace('/', '')
    if not product.ssid.isdigit():
        product.ssid = product.url.split('/')[-2].replace('-review', '')

    product.category = data.xpath('(//a[contains(@class, "category-link")]/text()[not(regexp:test(., "Reviews|Other Products|News"))])[last()]').string()
    if not product.category:
        product.category = "Tech"

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time[@class="date"]/text()').string()
    if date:
        review.date = ' '.join(date.split()[:3])

    author = data.xpath('//div[@class="author"]/a/text()').string()
    author_url = data.xpath('//div[@class="author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//span[contains(., "Overall:")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = float(grade_overall.count('⭐'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    grade_overall = data.xpath('//h4[contains(., "Overall Rating")]/following-sibling::p[1]//img/@src').string()
    if grade_overall and 'Please+Choose+Rating' not in grade_overall:
        grade_overall = grade_overall.split('/')[-1].replace('.png', '')
        if '_h' in grade_overall:
            grade_overall = float(grade_overall.replace('_h', '')) + 0.5

        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath('//span[contains(., "⭐") and not(contains(., "Overall:"))]')
    for grade in grades:
        grade = grade.xpath('.//text()').string(multiple=True)
        grade_name = grade.split(':')[0]
        grade_val = float(grade.count('⭐'))
        review.grades.append(Grade(name=grade_name, value=grade_val, best=5.0))

    grades = data.xpath('//div[@class="quality-ratings"]/ul/li[not(@class)]')
    for grade in grades:
        grade_name = grade.xpath('h4//text()').string(multiple=True)
        grade_val = grade.xpath('p//@src').string().split('/')[-1].replace('.png', '')
        if 'Please+Choose+Rating' not in grade_val:
            if '_h' in grade_val:
                grade_val = float(grade_val.replace('_h', '')) + 0.5

            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    grades = data.xpath('//p[preceding-sibling::h3[1][contains(., "Rating")]]')
    for grade in grades:
        grade_name = grade.xpath('strong/text()').string()
        grade_val = grade.xpath('text()').string(multiple=True)
        if grade_name and grade_val:
            grade_name = grade_name.strip(' :')
            grade_val = grade_val.strip(' :').split('/')[0]
            if grade_val and float(grade_val) > 0:
                if 'overall' in grade_name:
                    review.grades.append((Grade(type='overall', value=float(grade_val), best=10.0)))
                else:
                    review.grades.append((Grade(name=grade_name, value=float(grade_val), best=10.0)))

    pros = data.xpath('(//h3[contains(., "Pros")]/following-sibling::*)[1]/li//text()[normalize-space(.)]')
    if not pros:
        pros = data.xpath('//p[@class="pros"]/text()[normalize-space(.)]')
    if not pros:
        pros = data.xpath('//p[contains(., "Pros")]/following-sibling::p[1]//text()[not(regexp:test(., "None|Cons"))][normalize-space(.)]')

    for pro in pros:
        pro = pro.string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h3[contains(., "Cons")]/following-sibling::*)[1]/li//text()[normalize-space(.)]')
    if not cons:
        cons = data.xpath('//p[@class="cons"]/text()[normalize-space(.)]')
    if not cons:
        cons = data.xpath('//p[contains(., "Cons")]/following-sibling::p[1]//text()[not(contains(., "None"))][normalize-space(.)]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@class="secondary_font"]//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h3[contains(., "Conclusion")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Final Verdict")]//text()[not(contains(., "Final Verdict"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[@class="bottomline"]/text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Bottom Line")]/following-sibling::p//text()').string(multiple=True)

    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h3[contains(., "Conclusion")]/preceding-sibling::p[not(preceding::h3[1][contains(., "Rating")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@id="post-container"]/p[not(preceding::h3[1][contains(., "Rating")] or contains(., "Final Verdict"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
