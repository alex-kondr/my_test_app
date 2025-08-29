from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://moviesgamesandtech.com/category/reviews/', use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h3[contains(@class, "entry-title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('review-', '')
    product.category = 'Tech'

    if data.xpath('//div[contains(@class, "category")]/a[contains(., "Gaming")]'):
        product.category = 'Gaming'

    product.name = context['title'].split('Review:')[-1].split('REVIEW:')[-1].split('Review :')[-1].split('Reviews:')[-1].split('Preview:')[-1].split('Review –')[-1].split(' Review')[0].split('Review of the')[-1].split('Review of')[-1].split('Review ')[-1].replace('Test ', '').replace(' gameplay video preview', '').replace('Hands-on Preview', '').replace('Hands-on review of the ', '').replace('Two minute review of the ', '').replace(' two minute review', '').replace('Hands-on review of the', '').replace('Preview –', '').split(' Preview ')[0].split(' preview, ')[0].replace('Testing an ', '').replace('Preview of ', '').replace(' hands-on Preview', '').replace(' Preview', '').replace('(Global Version)', '').replace('(Spoiler Free)', '').replace('Hands-on preview of ', '').replace('A preview of ', '').replace('Two minute review of ', '').replace('Two-minute review of ', '').strip(' :.')
    if product.name.endswith('') == ' review':
        product.name = product.name.replace(' review', '').strip()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[span[contains(@class, "author-by")]]/a[contains(@class, "author-name")]/text()').string()
    author_url = data.xpath('//div[span[contains(@class, "author-by")]]/a[contains(@class, "author-name")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[contains(@class, "review-final-score")]/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall)
        best_grade = grade_overall if grade_overall > 10 else 10.0
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=best_grade))

    pros = data.xpath('(//p|//h4|//h5)[contains(., "Pros:")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[strong[normalize-space(text())="Pro"]]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//h4[contains(@class, "plus")]/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[contains(., "Pros:")]/following-sibling::p[1]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//div[contains(@class, "review-summary-content")]/text()[starts-with(normalize-space(.), "+")]')
        for pro in pros:
            pro = pro.string()
            if pro.count('+') > 1:
                pros_cons = pro.split('\n')
                for pro_con in pros_cons:
                    if pro_con.startswith('+'):
                        pro = pro_con.strip(' +-.*')
                        if len(pro) > 1:
                            review.add_property(type='pros', value=pro)

                    elif pro_con.startswith('-'):
                        con = pro_con.strip(' +-.*')
                        if len(pro) > 1:
                            review.add_property(type='cons', value=con)

                continue

            pro = pro.strip(' +-.*')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p|//h4|//h5)[contains(., "Cons:")]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[strong[normalize-space(text())="Con"]]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//h4[contains(@class, "minus")]/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[strong[contains(., "Cons")]]/following-sibling::p[1]')
    if not cons:
        cons = data.xpath('//p[contains(., "Cons:")]/following-sibling::p[1]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//div[contains(@class, "review-summary-content")]/text()[starts-with(normalize-space(.), "-")]')
        for con in cons:
            con = con.string().strip(' +-.*')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//div[contains(@class, "single_subtitle")]/div[contains(@class, "block-inner")]/p//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//h2[regexp:test(., "Conclusion|Verdict|Final Thoughts")]/following-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[(strong|b)[regexp:test(., "Conclusion|Verdict|Final Thoughts")]]/following-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[(strong|b)[regexp:test(., "Conclusion|Verdict|Final Thoughts")]]/following-sibling::div/p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[contains(@class, "review-summary-content")]/p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Conclusion:")]/following-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[regexp:test(., "Conclusion|Verdict|Final Thoughts")]/preceding-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[(strong|b)[regexp:test(., "Conclusion|Verdict|Final Thoughts")]]/preceding-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[contains(., "Conclusion:")]/preceding-sibling::p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "block-inner") and not(parent::div[contains(@class, "single_subtitle")])]/p[not(regexp:test(., "Pros:|Cons:|more information|Full disclosure|specification|http://|Speed:|Comments:|Conclusion:", "i") or strong[regexp:test(., "Pro|Con")])]//text()').string(multiple=True)

    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
