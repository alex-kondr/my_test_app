from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request('https://hothardware.com/reviews'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath("text()").string().replace('&amp;', '&')
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//a[contains(text(), "Next") and contains(@href, "pageindex")]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' (Review): ')[0].split(' Review: ')[0].split(' Preview: ')[0].split(' Review')[0].split(' Tested: ')[0].split(': Testing ')[0].split(' Beta Preview')[0].replace(' Tested', '').replace(' Preview', '').replace('Preview: ', '').replace(' PREview', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('-review', '')

    product.category = data.xpath("//div[@class='breadcrumb']/a[@class='blue last' and not(contains(., 'Review') or contains(., 'News'))]//text()").string()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = product.url

    date = data.xpath('//span[@class="dt-published"]/text()').string()
    if date:
        review.date = date.split(', ', 1)[-1].rsplit(', ', 1)[0]

    author = data.xpath('//a[contains(@class, "author")]//text()').string(multiple=True)
    author_url = data.xpath('//a[contains(@class, "author")]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath('//td[div//img[@alt="hot flat"]]//ul/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//td[div//img[@alt="not flat"]]//ul/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    is_recommended = data.xpath('//img[contains(@data-src, "hothardware_recommended")]')
    if is_recommended:
        review.add_property(type='is_recommended', value=True)

    summary = data.xpath('//table[@align="center"]//span/em//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h3|//h2)[contains(., "The Verdict")]/following-sibling::text()|(//h3|//h2)[contains(., "The Verdict")]/following-sibling::*//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h3|//h2)[contains(., "The Verdict")]/following-sibling::text()|(//h3|//h2)[contains(., "The Verdict")]/following-sibling::*//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h3|//h2)[contains(., "Conclusion")]/following-sibling::text()|(//h3|//h2)[contains(., "Conclusion")]/following-sibling::*//text()').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@class="cn-body e-content"]//text()[preceding::table[@align="center"] and not((preceding::h3|preceding::h2)[contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion")] or contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion") or ancestor::li or parent::h3)]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="cn-body e-content"]//text()[preceding::li[@class="pages-menu"] and not((preceding::h3|preceding::h2)[contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion")] or contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion") or ancestor::li or parent::h3)]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="cn-body e-content"]//text()[not((preceding::h3|preceding::h2)[contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion")] or contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion") or ancestor::li or parent::h3)]').string(multiple=True)

    pages = data.xpath('//li[@class="pages-menu"]/a|//li[@class="pages-menu"]//li')
    if pages:
        for page in pages:
            title = page.xpath('.//text()').string(multiple=True)
            url = page.xpath('.//@href').string()
            review.add_property(type='pages', value=dict(title=title, url=url))

        session.do(Request(url), process_review_last, dict(product=product, review=review, excerpt=excerpt, summary=summary))

    elif excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)


def process_review_last(data, context, session):
    review = context['review']

    conclusion = data.xpath('(//h3|//h2)[contains(., "The Verdict")]/following-sibling::text()|(//h3|//h2)[contains(., "The Verdict")]/following-sibling::*//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h3|//h2)[contains(., "The Verdict")]/following-sibling::text()|(//h3|//h2)[contains(., "The Verdict")]/following-sibling::*//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h3|//h2)[contains(., "Conclusion")]/following-sibling::text()|(//h3|//h2)[contains(., "Conclusion")]/following-sibling::*//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//text()[(preceding::h3|preceding::h2)[contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion")]][not(preceding::div[contains(@class, "cn-footer")] or ancestor::div[contains(@class, "cn-footer")])]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//div[@class="cn-body e-content"]//text()[not(ancestor::li or parent::h3)]').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    is_recommended = data.xpath('//img[contains(@data-src, "hothardware_recommended")]')
    if is_recommended:
        review.add_property(type='is_recommended', value=True)

    if data.xpath('(//h3|//h2)[contains(., "The Verdict") or contains(., "The Verdict") or contains(., "Conclusion")]'):
        excerpt = data.xpath('//div[@class="cn-body e-content"]//text()[not((preceding::h3|preceding::h2)[contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion")] or contains(., "Summary") or contains(., "The Verdict") or contains(., "Conclusion") or ancestor::li or parent::h3)]').string(multiple=True)
        context['excerpt'] += ' ' + excerpt

    if context['excerpt']:
        excerpt = context['excerpt']

        if context['summary']:
            excerpt = excerpt.replace(context['summary'], '').strip()

        if conclusion:
            excerpt = excerpt.replace(conclusion, '').strip()

        review.add_property(type='excerpt', value=excerpt)

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
