from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request("https://www.amateurphotographer.co.uk/"), process_frontpage, dict())


def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "menu-item")][a[text()="Reviews"]]//li/a')
    for cat in cats:
        name = cat.xpath('text()').string().replace(' reviews', '').strip()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))


def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='posts-list']/li[.//h2]")
    for rev in revs:
        title = rev.xpath(".//h2/text()").string()
        ssid = rev.xpath("@class").string().split('-')[1].split()[0].strip()
        url = rev.xpath(".//a/@href").string()
        author = rev.xpath('.//p[@class="author"]/text()').string()

        grade_overall = rev.xpath('.//span[contains(@class, "rating")][not(contains(@class, "not"))]/@class').string()
        if grade_overall:
            grade_overall = float(grade_overall.split('rating-')[1].replace('-', '.'))

        session.queue(Request(url), process_review, dict(context, url=url, author=author, grade_overall=grade_overall, title=title, ssid=ssid))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.ssid = context["ssid"]
    product.url = context["url"]
    product.category = context["cat"]
    product.manufacturer = data.xpath('//li[h3[contains(text(), "Manufacturer")]]//a/text()').string()
    product.name = context["title"].split('|')[0].split(" review")[0].split(" Review")[0].split("Review:")[-1].split(" Test")[0].split("a long")[0].split("field test")[0].split("the latest camera")[0].strip()

    review = Review()
    review.type = "pro"
    review.ssid = product.ssid
    review.url = context["url"]
    review.title = context["title"]
    review.date = data.xpath('//body/p[@class="date"]/text()').string()

    author = context.get('author')
    if author:
        author = author.replace('by ', '').strip()
        review.authors.append(Person(name=author, ssid=author))

    if context['grade_overall']:
        review.grades.append(Grade(type='overall', value=context['grade_overall'], best=5.0))

    grades = data.xpath('//div[@class="desktop-only"]//ul[@class="ratings"]/li')
    for grade in grades:
        name = grade.xpath("h3/text()").string()
        value = grade.xpath("p/text()").string()
        if value and 'overall' not in name.lower():
            value = value.split('out')[0].replace(':', '').replace('-', '.').strip()
            if not value or '/' in value:
                value = 1.0
            else:
                value = float(value)
            review.grades.append(Grade(name=name, value=value, best=5.0))

    pros = data.xpath('(//div[@class="desktop-only"]//p[@class="pros"]/text())[normalize-space(.)]').strings()
    for pro in pros:
        pro = pro.replace('+', '').replace('- ', '').strip()
        review.add_property(type="pros", value=pro)

    cons = data.xpath('(//div[@class="desktop-only"]//p[@class="cons"]/text())[normalize-space(.)]').strings()
    for con in cons:
        con = con.replace('+ ', '').replace('- ', '').strip()
        if con.startswith('-'):
            con = con[1:]
        review.add_property(type="cons", value=con)

    summary = data.xpath('//div[@class="post-excerpt-content"]/text()').string()
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/following-sibling::p[not(@class)][not(li)][not(em)][not(br)][not(contains(., "Read our full"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//li[h3[contains(text(), "Verdict") or contains(., "verdict") or contains(., "Conclusion")]]/p/text()').string()

    if data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/text()').string():
        excerpt = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/preceding-sibling::p[not(@class)][not(li)][not(em)][not(contains(., "Read our full"))]//text()').string(multiple=True)
    else:
        excerpt = data.xpath('//div[@class="editable-content"]/p[not(@class)][not(li)][not(em)][not(contains(., "pecification"))][not(contains(., "Read our full"))]//text()').string(multiple=True)

    context['product'] = product
    context['conclusion'] = conclusion
    context['excerpt'] = excerpt

    next_url = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    if next_url:
        review.add_property(type='pages', value=dict(title=review.title + ' - page 1', url=context['url']))
        session.do(Request(next_url), process_review_next, dict(context, review=review, url=next_url, page=2))
    else:
        context['review'] = review
        context['page'] = 1

        process_review_next(data, context, session)


def process_review_next(data, context, session):
    review = context['review']

    page = context['page']
    if page > 1:
        review.add_property(type="pages", value=dict(title=review.title+' - page '+str(page), url=context["url"]))

        conclusion = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/following-sibling::p[not(@class)][not(li)][not(em)][not(br)][not(contains(., "Read our full"))]//text()').string(multiple=True)
        if not conclusion:
            conclusion = data.xpath('//li[h3[contains(text(), "Verdict") or contains(., "verdict") or contains(., "Conclusion")]]/p/text()').string()
        if conclusion:
            context['conclusion'] = conclusion

        if data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/text()').string():
            excerpt = data.xpath('//div[@class="editable-content"]/*[contains(., "Verdict") or contains(., "verdict") or contains(., "Conclusion")]/preceding-sibling::p[not(@class)][not(li)][not(em)][not(contains(., "Read our full"))]//text()').string(multiple=True)
        else:
            excerpt = data.xpath('//div[@class="editable-content"]/p[not(@class)][not(li)][not(em)][not(contains(., "pecification"))][not(contains(., "Read our full"))]//text()').string(multiple=True)
        if excerpt:
            context['excerpt'] += ' ' + excerpt

    next_url = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    if next_url:
        session.do(Request(next_url), process_review_next, dict(context, review=review, url=next_url, page=page + 1))

    elif context['excerpt']:
        product = context['product']

        if context['conclusion']:
            review.add_property(type='conclusion', value=context['conclusion'])

        review.add_property(type="excerpt", value=context['excerpt'])

        product.reviews.append(review)

        session.emit(product)
