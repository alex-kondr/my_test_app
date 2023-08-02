from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://www.amateurphotographer.co.uk/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "menu-item")][a[text()="Reviews"]]//li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string().replace(' reviews', '').strip()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='posts-list']/li[.//h2]")
    for rev in revs:
        context['title'] = rev.xpath(".//h2/text()").string()
        context['ssid'] = rev.xpath("@class").string().split('-')[1].split()[0].strip()
        context['author'] = rev.xpath('.//p[@class="author"]/text()').string().replace('by ', '').strip()
        url = rev.xpath(".//a/@href").string()

        grade_overall = rev.xpath('.//span[contains(@class, "rating")][not(contains(@class, "not"))]/@class').string()
        if grade_overall:
            grade_overall = float(grade_overall.split('rating-')[1].replace('-', '.'))

        session.queue(Request(url), process_review, dict(context, url=url, grade_overall=grade_overall))

    next_page = data.xpath('//link[@rel="next"]/@href').string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.ssid = context["ssid"]
    product.url = context["url"]
    product.category = context["cat"]
    product.manufacturer = data.xpath('//li[h3[contains(text(), "Manufacturer")]]//a/text()').string()
    product.name = context["title"].split('|')[0].split(" review")[0].split(" Test")[0].strip()

    review = Review()
    review.type = "pro"
    review.ssid = product.ssid
    review.url = context["url"]
    review.title = context["title"]
    review.date = data.xpath('//body/p[@class="date"]/text()').string()
    review.authors.append(Person(name=context['author'], ssid=context['author']))

    if context['grade_overall']:
        review.grades.append(Grade(type='overall', value=context['grade_overall'], best=5.0))

    grades = data.xpath('//div[@class="desktop-only"]//ul[@class="ratings"]/li')
    for grade in grades:
        name = grade.xpath("h3/text()").string()
        value = grade.xpath("p/text()").string()
        if value and 'overall' not in name.lower():
            value = float(value.split('out')[0].replace(':', '').replace('-', '.').strip())
            review.grades.append(Grade(name=name, value=value, best=5.0))

    pros = data.xpath('(//div[@class="desktop-only"]//p[@class="pros"]/text())[normalize-space(.)]').strings()
    for pro in pros:
        pro = pro.replace('+ ', '').replace('- ', '').strip()
        review.add_property(type="pros", value=pro)

    cons = data.xpath('(//div[@class="desktop-only"]//p[@class="cons"]/text())[normalize-space(.)]').strings()
    for con in cons:
        con = con.replace('- ', '').strip()
        review.add_property(type="cons", value=con)

    summary = data.xpath('//div[@class="post-excerpt-content"]/text()').string()
    if summary:
        review.add_property(type="summary", value=summary)

    context['conclusion'] = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict")]/following-sibling::*[not(@class)][not(li)][not(em)][not(strong)][not(contains(., "Specifications"))]//text()[normalize-space(.)]').string(multiple=True)
    if not context['conclusion']:
        context['conclusion'] = data.xpath('//li[h3[contains(text(), "Verdict") or contains(., "verdict")]]/p/text()').string()

    context['excerpt'] = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict")]/preceding-sibling::*[not(@class)][not(li)][not(em)]//text()[normalize-space(.)]').string(multiple=True)
    if not context['excerpt']:
        context['excerpt'] = data.xpath('//div[@class="editable-content"]/*[not(@class)][not(li)][not(em)][not(contains(., "Specifications"))]//text()').string(multiple=True)

    context['product'] = product

    next_page = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    if next_page:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=context['url']))
        session.do(Request(next_page), process_review_next, dict(context, review=review, url=next_page, page=2))
    else:
        context['review'] = review
        context['page'] = 1

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context['page']
    if page > 1:
        review.add_property(type="pages", value=dict(title=review.title+' - page '+str(page), url=context["url"]))

        conclusion = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict")]/following-sibling::*[not(@class)][not(li)][not(em)][not(strong)][not(contains(., "Specifications"))]//text()[normalize-space(.)]').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//li[h3[contains(text(), "Verdict")]]/p/text()').string()
        if conclusion:
            context['conclusion'] = conclusion

        excerpt = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict")]/preceding-sibling::*[not(@class)][not(li)][not(em)]//text()[normalize-space(.)]').string(multiple=True)
        if not excerpt:
            excerpt = data.xpath('//div[@class="editable-content"]/*[not(@class)][not(li)][not(em)][not(contains(., "Specifications"))]//text()').string(multiple=True)
        if excerpt:
            context['excerpt'] += ' ' + excerpt

    next_page = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    if next_page:
        review, excerpt = session.do(Request(next_page), process_review_next, dict(context, review=review, url=next_page, page=page + 1))

    elif context['excerpt']:
        product = context['product']

        if context['conclusion']:
            review.add_property(type='conclusion', value=context['conclusion'])

        review.add_property(type="excerpt", value=context['excerpt'])

        product.reviews.append(review)

        session.emit(product)
