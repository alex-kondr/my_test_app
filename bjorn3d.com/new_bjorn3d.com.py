from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers=[SessionBreak(max_requests=4000)]
    session.queue(Request('https://bjorn3d.com/category/reviews-articles/', use='curl', force_charset='utf-8'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath("//h2[@class='post-box-title']/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    nexturl = data.xpath("//span[@id='tie-next-page']/a/@href").string()
    if nexturl:
        session.queue(Request(nexturl, use='curl', force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace(': A Preview', '').replace(' Preview', '').replace(' Review', '').replace(' review', '').replace(' Tested', '').replace('SLI Tests: ', '').replace(' REVIEW' ,'').replace(' Testbench', '').replace(' (+ SLI 285 Testing)', '').replace('Preview of the ', '').replace(' preview', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-review', '')

    product.category = data.xpath('//div[nav[@id="crumbs"]]/a[not(@id or regexp:test(., "Reviews|Article|Home|Preview"))]//text()[normalize-space(.)]').string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//span[@class="post-meta-author"]/a/text()').string()
    author_url = data.xpath('//span[@class="post-meta-author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="entry"]/div[@data-id]/p[not(@class or preceding-sibling::h2[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::h3[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry"]/p[not(@class or preceding-sibling::h2[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::h3[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(@class or preceding-sibling::h2[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::h3[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)

    pages = data.xpath('(//div[contains(span/text(), "Jump to section")])[1]//li/a')
    if not pages:
        pages = data.xpath('//div[@class="page-link"]/span|//div[@class="page-link"]/a')

    if pages:
        for page in pages:
            page_title = page.xpath(".//text()").string(multiple=True)
            if len(page_title) < 3:
                page_title = review.title + ' - Pagina ' + page_title

            page_url = page.xpath("@href").string()
            if not page_url:
                page_url = review.url

            page_url = page_url.split('#')[0]
            review.add_property(type='pages', value=dict(title=page_title, url=page_url))

        session.do(Request(page_url, use='curl', force_charset='utf-8'), process_review_last, dict(excerpt=excerpt, review=review, product=product, pages=True))

    else:
        context['excerpt'] = excerpt
        context['product'] = product
        context['review'] = review
        process_review_last(data, context, session)


def process_review_last(data, context, session):
    review = context['review']

    grade_overall = data.xpath("//div[@class='review-final-score']/h3/text()").string()
    if not grade_overall:
        grade_overall = data.xpath('//tr[contains(td, "Total")]/td[@class="second_column"]/text()').string()

    if grade_overall and float(grade_overall) > 10:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))
    elif grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    if not grade_overall:
        grade_overall = data.xpath('//div[@class="review-final-score"]/span[contains(@class, "stars")]//@style').string()
        if grade_overall:
            grade_overall = float(grade_overall.split(':')[-1].replace('%', '')) / 20
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    grades = data.xpath("//div[@class='review-item']")
    for grade in grades:
        grade_text = grade.xpath("./h5//text()").string(multiple=True)

        if grade_text and ' - ' in grade_text:
            grade_name, grade_val = grade_text.split(' - ')
            grade_val = float(grade_val.replace('%', ''))
            if grade_val > 10:
                review.grades.append(Grade(name=grade_name, value=grade_val, best=100.0))
            elif grade_val > 0:
                review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))
        else:
            grade_val = grade.xpath('span[contains(@class, "stars")]//@style').string()
            grade_val = float(grade_val.split(':')[-1].replace('%', '')) / 20
            review.grades.append(Grade(name=grade_text, value=grade_val, best=5.0))

    if not grades:
        grades = data.xpath('//table[@class="score_table"]//tr')
        for grade in grades:
            grade_name = grade.xpath('td[@class="first_column"]/text()').string()
            grade_val = grade.xpath('td[@class="score_column"]/text()').string()
            if grade_name and grade_val and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=grade_val, best=10.0))

    pros = data.xpath('(//p[regexp:test(normalize-space(strong),"^Pro[s:\n]")]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    if not pros:
        pros = data.xpath('//td[@class="pro_column"]//text()[normalize-space()]')
        for pro in pros:
            pro = pro.string()
            if pro:
                pro = pro.strip(' +-*.:;•,–')
                if len(pro) > 1:
                    review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[regexp:test(normalize-space(strong),"^Con[s:\n]")]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    if not cons:
        cons = data.xpath('//td[@class="con_column"]//text()[normalize-space()]')
        for con in cons:
            con = con.string()
            if con:
                con = con.strip(' +-*.:;•,–')
                if len(con) > 1:
                    review.add_property(type='cons', value=con)

    conclusion = data.xpath("//div[@class='split-container split-template-1']/h3[contains(.,'Conclusion')]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='split-container split-template-1']/h3[contains(.,'Final Thoughts')]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='entry']/h2[contains(.,'CONCLUSION')]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='entry']/h2[contains(.,'Conclusion')]/following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")]][not(preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace(u'�', '').strip()
        review.add_property(type='conclusion', value=conclusion) 

    if not conclusion and context.get('pages'):
        excerpt = data.xpath('//div[@class="entry"]/div[@data-id]/p[not(@class or preceding-sibling::h2[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::h3[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="entry"]/p[not(@class or preceding-sibling::h2[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::h3[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//body//p[not(@class or preceding-sibling::h2[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::h3[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(.,"Conclusion|Final Thoughts", "i")] or preceding-sibling::p[regexp:test(normalize-space(strong),"^Pro[s:\n]|^Con[s:\n]")] or regexp:test(normalize-space(strong),"Pro[s:\n]|^Con[s:\n]"))]//text()').string(multiple=True)

        if excerpt:
            context['excerpt'] = context.get('excerpt', '') + ' ' + excerpt

    if context['excerpt']:
        excerpt = context['excerpt'].replace(u'�', '').strip()
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
