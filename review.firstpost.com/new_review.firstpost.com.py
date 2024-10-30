from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://api-mt.firstpost.com/nodeapi/v1/mfp/get-article-list?count=50&fields=images%2Cdisplay_headline%2Cweburl_r%2Cpost_type%2Cgallery%2Cstory_id%2Cvideo_type%2Ccreated_at%2Cupdated_at&filter=%7B%22categories.slug%22%3A%22reviews%22%7D&offset=0&section=category&sectionCount=7&sectionFilter=%7B%22categories.slug%22%3A%22reviews%22%7D&sortBy=updated_at&subSection=reviews', use='curl', max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    data_json = simplejson.loads(data.content)

    revs = data_json.get('data', [])
    for rev in revs:
        title = rev.get('display_headline')
        url = 'https://www.firstpost.com' + rev.get('weburl_r', '')
        session.queue(Request(url, use='curl', max_age=0), process_review, dict(title=title, url=url))


    revs_cnt = data_json.get('total', 0)
    offset = context.get('offset', 0) + 50
    if offset < revs_cnt:
        next_url = 'https://api-mt.firstpost.com/nodeapi/v1/mfp/get-article-list?count=50&fields=images%2Cdisplay_headline%2Cweburl_r%2Cpost_type%2Cgallery%2Cstory_id%2Cvideo_type%2Ccreated_at%2Cupdated_at&filter=%7B%22categories.slug%22%3A%22reviews%22%7D&offset={offset}&section=category&sectionCount=7&sectionFilter=%7B%22categories.slug%22%3A%22reviews%22%7D&sortBy=updated_at&subSection=reviews'.format(offset=offset)
        session.queue(Request(next_url, use='curl', max_age=0), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' Preview ')[0].split(' Review')[0].split(' review:')[0].split(' Preview: ')[0].replace('Review: ', '').replace('Review ', '').replace(' reviewed', '').replace(' review', '').replace('&amp;', ' - ').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]
    product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title'].replace('&amp;', ' - ')
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[@class="art-dtls-info"]/a/text()').string()
    author_url = data.xpath('//div[@class="art-dtls-info"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[contains(., "Rating:")]/text()[regexp:test(., "\d.?\d?/\d")]').string()
    if grade_overall:
        grade_overall = float(grade_overall.split('/')[0].split()[-1])
        review.grades.append(Grade(type='overall', value=grade_overall, best=5.0))

    pros = data.xpath('//p[strong[contains(., "Pros")]]/text()')
    for pro in pros:
        pro = pro.string(multiple=True)
        if pro and '- ' in pro:
            pros_ = pro.split('- ')
        else:
            pros_ = pro.split('– ')
        for pro in pros_:
            pro = pro.strip(' -–+')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[strong[contains(., "Cons")]]/text()')
    # https://www.firstpost.com/tech/news-analysis/sony-kd-50x70l-google-tv-review-12777812.html
    for con in cons:
        con = con.string(multiple=True)
        if con and '- ' in con:
            cons_ = con.split('- ')
        else:
            cons_ = con.split('– ')
        for con in cons_:
            con = con.strip(' -–+')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    summary = data.xpath('//span[@class="less-cont"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('//p[strong[regexp:test(., "verdict", "i")]]/text()|//p[strong[regexp:test(., "verdict", "i")]]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[regexp:test(., "verdict", "i")]]/preceding-sibling::p[not(strong[regexp:test(., "Pros|Cons")] or regexp:test(., "Rating:|Click here for"))]//text()[not(contains(., "Review:"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "content")]/p[not(strong[regexp:test(., "Pros|Cons")] or regexp:test(., "Rating:|Click here for"))]//text()[not(contains(., "Review:"))]').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
