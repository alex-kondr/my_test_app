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

    next_url = data.xpath("//a[@class='page-link next page-numbers']//@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl", force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.url = context["url"]
    product.ssid = product.url.split("/")[-3]
    product.name  = context["title"].split("Review of ")[-1].split('Preview:')[0].split(" Review")[0].split("Review: ")[-1]

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
    if not grade:
        grade = data.xpath('//strong[contains(text(), "Overall score")]//parent::p//text()').string(multiple=True)
    if grade and 'Verdict:' in grade:
        grade = grade.split(' ')[-1].split('/')[0]
        review.grades.append(Grade(type="overall", value=float(grade), best=5.0))
    elif grade and ':' in grade:
        grade = grade.split(': ')[-1].split(" ")[0].split('/')[0]
        review.grades.append(Grade(type="overall", value=float(grade), best=10.0))

    conclusion = data.xpath('(//strong[contains(text(), "The Verdict") or contains(text(), "Conclusion") or contains(text(), "Final word") or contains(text(), "Summary")]/following-sibling::text()|//strong[contains(text(), "The Verdict") or contains(text(), "Conclusion") or contains(text(), "Final word")]/following::p[not(strong)]/text())[string-length() > 3]').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('(//strong[contains(text(), "The Verdict") or contains(text(), "Conclusion") or contains(text(), "Final word") or contains(text(), "Summary")]/preceding::p//text()|//strong[contains(text(), "The Verdict") or contains(text(), "Conclusion") or contains(text(), "Final word") or contains(text(), "Summary")]/preceding-sibling::text())[not(contains(., "Reviewed on "))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//strong[contains(text(), "What Impressed") or contains(text(), "Playtime") or contains(text(), "Sweet") or contains(text(), "The Good") or contains(text(), "The good")]/preceding::p//text()|//strong[contains(text(), "What Impressed") or contains(text(), "Playtime") or contains(text(), "Sweet") or contains(text(), "The Good") or contains(text(), "The good")]/preceding-sibling::text())[not(contains(., "Reviewed on "))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//strong[contains(text(), "Overall score")]/preceding::p//text()[not(contains(., "Reviewed on "))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('(//p[contains(text(), "Score: ")]/preceding::p//text()|//strong[contains(text(), "Score: ")]/preceding::p//text())[not(contains(., "Reviewed on "))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//i[contains(text(), "Follow this author")]/preceding::p[not(strong/em)]//text()[not(contains(., "Reviewed on "))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="post-body"]//text()[not(contains(., "Reviewed on "))]').string(multiple=True)

    if excerpt:
        review.add_property(type="excerpt", value=excerpt)

        product.reviews.append(review)

        session.emit(product)
