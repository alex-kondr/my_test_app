from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.pcquest.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="small-post"]/span[1]/a[not(span)]')
    for rev in revs:
        title = rev.xpath('@aria-label').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    title = data.xpath('//a[@class="clickable" and img]/img/@alt').string()
    url = data.xpath('//a[@class="clickable" and img]/@href').string()
    session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Gaming- Review', '').replace('Review:', '').replace(':Review', '').replace(' Review', '').replace('Review of', '').replace('review: ', '').replace('review-', '').replace(' review', '').replace(' REVIEW', '').strip()
    product.url = context['url']

    product.ssid = product.url.split('-')[-1].replace('/', '')
    if not product.ssid.isdigit():
        product.ssid = product.url.split('/')[-2].replace('-review', '')

    cats = data.xpath('//a[contains(@class, "category-link")]/text()[not(contains(., "Reviews") or contains(., "News"))]').strings()
    if cats:
        product.category = '|'.join(cats)
    else:
        product.category = "Tech"

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[time[@class="date"]]//text()').string(multiple=True)
    if date:
        review.date = ' '.join(date.split()[:3])

    author = data.xpath('//meta[@name="author"]/@content').string()
    if author:
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
        grade_name = grade.xpath('h4/span/text()').string()
        grade_val = grade.xpath('p//@src').string().split('/')[-1].replace('.png', '')
        if 'Please+Choose+Rating' not in grade_val:
            if '_h' in grade_val:
                grade_val = float(grade_val.replace('_h', '')) + 0.5

            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=5.0))

    pros = data.xpath('//p[@class="pros"]/span/text()').strings()
    if not pros:
        pros = data.xpath('//p[contains(., "Pros")]/following-sibling::p[1]//text()[not(contains(., "None"))]').strings()
    for pro in pros:
        pro = pro.replace('None', '').strip()
        if pro and len(pro) > 1:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[@class="cons"]/span/text()').strings()
    if not cons:
        cons = data.xpath('//p[contains(., "Cons")]/following-sibling::p[1]//text()[not(contains(., "None"))]').strings()
    for con in cons:
        con = con.replace('None', '').strip()
        if con and len(con) > 1:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@class="secondary_font"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[@class="bottomline"]/span/text()').string()
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Bottom Line")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@id="postContent"]/p//text()').string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
