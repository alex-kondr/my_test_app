from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://www.exophase.com/tag/review/", use="curl", force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    for prod in data.xpath("//div[contains(@id, 'post-')]//h3[contains(@class, 'mediumHeading')]//a"):
        url = prod.xpath("@href").string()
        title = prod.xpath("text()").string(multiple=True)
        if url and title:
            session.queue(Request(url, use="curl", force_charset='utf-8'), process_review, dict(url=url, title=title))

    nexturl = data.xpath("//a[@class='page-link next page-numbers']//@href").string()
    if nexturl:
        session.queue(Request(nexturl, use="curl", force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context["url"]
    product.ssid = product.url.split("/")[-3]

    product.name  = context["title"].split("Review of ")[-1].split(" Review")[0].split("Review: ")[-1]

    category = data.xpath("//div[@class='post-body']//p[contains(., 'Reviewed on')]//text()").string(multiple=True)
    if category:
        product.category = "Games|" + category.split("Reviewed on ")[-1].split(" ")[0]
    else:
        product.category = "Games"

    review = Review()
    review.type = "pro"
    review.title = context["title"]
    review.url = context["url"]
    review.ssid = product.ssid

    date = data.xpath("//h4[@class='mt-3 mb-3']//span//following-sibling::text()").string(multiple=True)
    if date:
        review.date = date.split(" @")[0]

    author = data.xpath("//span[@class='author']//text()").string()
    author_url = data.xpath("//a[@class='follow-me']//@href").string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath("(//strong[contains(text(), 'What Impressed') or contains(text(), 'Playtime') or contains(text(), 'Sweet') or contains(text(), 'The Good') or contains(text(), 'The good')]//parent::p/following-sibling::ul[1]//li//text())[normalize-space(.)][not(contains(., 'Sweet'))]")
    "//strong[contains(text(), 'What Impressed') or contains(text(), 'Playtime') or contains(text(), 'Sweet') or contains(text(), 'The Good') or contains(text(), 'The good')]/parent::p//following-sibling::p[1]//text()"
    if not pros:
        pros = data.xpath("(//strong[contains(text(), 'What Impressed') or contains(text(), 'Playtime') or contains(text(), 'Sweet') or contains(text(), 'The Good') or contains(text(), 'The good')]//following-sibling::text())[normalize-space(.)][not(contains(., 'Sweet'))]")
    for pro in pros:
        pro = pro.string().replace('–', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath("//strong[contains(text(), 'What Didn’t') or contains(text(), 'Sticky') or contains(text(), 'Detention') or contains(text(), 'The Bad') or contains(text(), 'The bad')]//parent::p//following-sibling::ul//li//text()[normalize-space(.)]")
    if not cons:
        cons = data.xpath("//strong[contains(text(), 'What Didn’t') or contains(text(), 'Sticky') or contains(text(), 'Detention') or contains(text(), 'The Bad') or contains(text(), 'The bad')]//following-sibling::text()[normalize-space(.)]")
    for con in cons:
        con = con.string().replace('–', '').strip()
        review.add_property(type='cons', value=con)

    grade = data.xpath("//strong[contains(text(), 'Score: ')]//parent::p//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'Verdict: ')]//parent::p//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'out of')]//parent::p//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'Score: ')]//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'Verdict: ')]//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'out of')]//text()").string(multiple=True)
    if grade:
        if 'Verdict:' in grade:
            grade = grade.split(' ')[-1].split('/')[0]
            review.grades.append(Grade(type="overall", value=float(grade), best=5.0))
        elif ':' in grade:
            grade = grade.split(': ')[-1].split(" ")[0]
            review.grades.append(Grade(type="overall", value=float(grade), best=10.0))

    summary = data.xpath("//strong[contains(text(), 'Summary')]//following-sibling::text()").string(multiple=True)
    if summary:
        summary = summary.replace('\n', ' ')
        review.properties.append(ReviewProperty(type="summary", value=summary))

    body = data.xpath('//div[@class="post-body"]//text()[normalize-space(.)]').string(multiple=True)
    '//strong[contains(text(), "The Verdict") or contains(text(), "Conclusion") or contains(text(), "Final word")]/following-sibling::text()|//strong[contains(text(), "The Verdict") or contains(text(), "Conclusion") or contains(text(), "Final word")]//parent::p//following-sibling::p//text()'

    if 'Conclusion' in body:
        conclusion = body.split('Conclusion')[-1]
    elif 'The Verdict' in body:
        conclusion = body.split('The Verdict')[-1]
    elif body and ('Final word' in body):
        conclusion = body.split('Final word')[-1]
    else:
        conclusion = None

    if conclusion:
        conclusion = conclusion.split('What Impressed')[0].split('Playtime')[0].split('Sweet')[0].split('The Good')[0].split('Follow this author')[0].split('Score')[0].replace('\n', ' ').strip()
        review.properties.append(ReviewProperty(type="conclusion", value=conclusion))

    if body:
        excerpt = body.split('Conclusion')[0].split('The Verdict')[0].split('Final word')[0].split('Summary')[0].split('What Impressed')[0].split('Playtime')[0].split('Sweet')[0].split('The Good')[0].split('Follow this author')[0].split('Score')[0].split('Follow this author')[0]
        review.properties.append(ReviewProperty(type="excerpt", value=excerpt.strip()))

        product.reviews.append(review)

        session.emit(product)