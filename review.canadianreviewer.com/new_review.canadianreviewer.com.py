from agent import *
from models.products import *


OPTIONS = """-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Connection: keep-alive' -H 'Cookie: JSESSIONID=90EBD8EBF9C9922FC29E44D90DD539B8.v5-web006; crumb=BbXdNLZGD7/9NTc3NzAxZGViMjZlZTBiNWM2YzhhNGYzNDIzOTkx' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Priority: u=0, i'"""


def run(context, session):
    session.queue(Request('http://www.canadianreviewer.com/cr/category/reviews', use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//h2[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if title and 'Canadian Reviewer Weekly' not in title:
            session.queue(Request(url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_review, dict(title=title, url=url))

    revs_cnt = context.get('revs_cnt')
    if not revs_cnt:
        revs_cnt = data.xpath('//h2[not(@class) and contains(text(), "Reviews")]/text()').string()

    if revs_cnt:
        revs_cnt = revs_cnt.rsplit(' ', 1)[-1].strip('( )')
        offset = context.get('offset', 0) + 4
        next_page = context.get('page', 1) + 1
        if offset < int(revs_cnt):
            next_url = 'https://www.canadianreviewer.com/cr/category/reviews?currentPage=' + str(next_page)
            session.queue(Request(next_url, use='curl', force_charset='utf-8', options=OPTIONS, max_age=0), process_revlist, dict(revs_cnt=revs_cnt, offset=offset, page=next_page))


def process_review(data, context, session):
    if not data.xpath('//div[@class="body"]/p[not(.//a)]'):
        return

    product = Product()
    product.ssid = context['url'].split('/')[-1].replace('.html', '').replace('review-', '')
    product.category = 'Tech'

    name = context['title']
    if not name:
        name = data.xpath('//h2[@class="title"]//text()').string(multiple=True)

    if 'Canadian Reviewer Weekly' in name:
        return

    product.name = name.replace('Review: ', '').replace(' Review', '').replace(' review', '').strip()

    product.url = data.xpath('//p[regexp:test(., "^The") and a[not(contains(@href, "canadianreviewer"))]]/a/@href').string()
    if not product.url:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//div[contains(@class, "entry-float-date")]//text()').string(multiple=True)

    author = data.xpath('//span[@class="posted-by"]/a/text()').string(multiple=True)
    author_url = data.xpath('//span[@class="posted-by"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//p[(./span|./strong)[regexp:test(text(), "\d out of \d")]]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.replace('Rating', '').split(' out of ')[0].strip(' :')
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    pros = data.xpath('//p[strong[contains(., "Pros")]]/following-sibling::p[(preceding-sibling::p[strong])[last()][contains(., "Pros")] and not(strong[regexp:test(., "Pros|Cons|Rating|Conclusion")])]')
    if not pros:
        pros = data.xpath('(//p[.//strong[contains(., "Hits:")]]/following-sibling::ul)[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.;•–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//p[strong[contains(., "Cons")]]/following-sibling::p[(preceding-sibling::p[strong])[last()][contains(., "Cons")] and not(strong[regexp:test(., "Pros|Cons|Rating|Conclusion")])]')
    if not cons:
        cons = data.xpath('(//p[.//strong[contains(., "Misses:")]]/following-sibling::ul)[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.;•–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]/following-sibling::p[not(strong[regexp:test(., "Pros|Cons|Rating|Conclusion")])]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[strong[contains(., "Conclusion")]]/following-sibling::div//text()[not(regexp:test(., "Pros|Cons|Rating|Conclusion|Hits:|Misses:|Rating:") or preceding::strong[regexp:test(., "Pros|Cons|Rating|Hits:|Misses:|Rating:")])]').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'\uFEFF', '').strip()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[strong[contains(., "Conclusion")]]/preceding-sibling::p[not(strong[regexp:test(., "Pros|Cons|Rating|Conclusion")] or preceding::strong[regexp:test(., "Pros|Cons|Rating|Conclusion")])]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//div[@class="body"]/p|//div[@class="body"]/div)[not(strong[regexp:test(., "Pros|Cons|Rating|Conclusion|Hits:|Misses:")] or preceding::strong[regexp:test(., "Pros|Cons|Rating|Conclusion|Hits:|Misses:")] or contains(., "Rating:"))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.replace(u'\uFEFF', '').strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
