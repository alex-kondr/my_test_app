from agent import *
from models.products import *


def process_productlist(data, context, session):
    for prod in data.xpath("//div[contains(@id, 'post-')]//h3[contains(@class, 'mediumHeading')]//a"):
        url = prod.xpath("@href").string()
        title = prod.xpath("text()").string(multiple=True)
        if url and title:
            session.queue(Request(url, use="curl"), process_review, dict(url=url, title=title))

    nexturl = data.xpath("//a[@class='page-link next page-numbers']//@href").string()
    if nexturl:
        session.queue(Request(nexturl, use="curl"), process_productlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context["url"]
    product.ssid = product.url.split("exophase.com/")[1].split("/")[0]

    name = context["title"]
    if "Review of " in name:
        name = name.split("Review of ")[1]
    name = name.split(" Review")[0]
    if "Review: " in name:
        name = name.split("Review: ")[1]
    product.name = name

    category = data.xpath("//div[@class='post-body']//p[contains(., 'Reviewed on')]//text()").string()
    if category:
        if "Reviewed on" in category:
            category = category.split("Reviewed on ")[1].split(" ")[0]
        product.category = "Games|" + category
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
    if author:
        author_url = data.xpath("//a[@class='follow-me']//@href").string()
        if author_url:
            review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
        else:
            review.authors.append(Person(name=author, ssid=author))

    pros = data.xpath("//strong[contains(text(), 'What Impressed') or contains(text(), 'Playtime') or contains(text(), 'Sweet') or contains(text(), 'The Good') or contains(text(), 'The good')]//parent::p/following-sibling::ul[1]//li//text()")
    if not pros:
        pros = data.xpath("//strong[contains(text(), 'What Impressed') or contains(text(), 'Playtime') or contains(text(), 'Sweet') or contains(text(), 'The Good') or contains(text(), 'The good')]//following-sibling::text()")
    for pro in pros:
        pro = pro.string()
        if pro:
            if '–' in pro:
                pro = pro.split('–')[-1].strip()
            review.add_property(type='pros', value=pro)

    cons = data.xpath("//strong[contains(text(), 'What Didn’t') or contains(text(), 'Sticky') or contains(text(), 'Detention') or contains(text(), 'The Bad') or contains(text(), 'The bad')]//parent::p//following-sibling::ul//li//text()")
    if not cons:
        cons = data.xpath("//strong[contains(text(), 'What Didn’t') or contains(text(), 'Sticky') or contains(text(), 'Detention') or contains(text(), 'The Bad') or contains(text(), 'The bad')]//following-sibling::text()")
    for con in cons:
        con = con.string()
        if con:
            if '–' in con:
                con = con.split('–')[-1].strip()
            review.add_property(type='cons', value=con)
               
    grade = data.xpath("//strong[contains(text(), 'Score: ')]//parent::p//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'Verdict: ')]//parent::p//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(text(), 'out of')]//parent::p//text()").string(multiple=True)
    if grade:
        if 'Verdict:' in grade:
            grade = grade.split(' ')[-1].split('/')[0]
            review.grades.append(Grade(name="Score", type="overall", value=float(grade), best=5.0))
        elif ':' in grade:
            grade = grade.split(': ')[-1].split(" ")[0]
            review.grades.append(Grade(name="Score", type="overall", value=float(grade), best=10.0))

    summary = data.xpath("//strong[contains(text(), 'Summary')]//following-sibling::text()").string(multiple=True)
    if summary:
        summary = summary.replace('\n', ' ')
        review.properties.append(ReviewProperty(type="summary", value=summary))

    conclusion = data.xpath("//strong[contains(text(), 'The Verdict') or contains(text(), 'Conclusion') or contains(text(), 'Final word')]//parent::p//following-sibling::p//text()").string(multiple=True)
    if conclusion:
        if 'What Impressed' in conclusion:
            conclusion = conclusion.split('What Impressed')[0]
        if 'Playtime' in conclusion:
            conclusion = conclusion.split('Playtime')[0]
        if 'Sweet' in conclusion:
            conclusion = conclusion.split('Sweet')[0]
        if 'The Good' in conclusion:
            conclusion = conclusion.split('The Good')[0]
        if 'Follow this author' in conclusion:
            conclusion = conclusion.split('Follow this author')[0]
        conclusion = conclusion.replace('\n', ' ')
        review.properties.append(ReviewProperty(type="conclusion", value=conclusion))

    excerpt = data.xpath("//div[@class='post-body']//p//text()").string(multiple=True)
    if excerpt:
        if 'Score:' in excerpt:
            excerpt = excerpt.split('Score:')[0]
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        excerpt = excerpt.replace('\n', ' ')
        review.properties.append(ReviewProperty(type="excerpt", value=excerpt))

    product.reviews.append(review)
    session.emit(product)


def run(context, session):
    session.queue(Request("https://www.exophase.com/tag/review/", use="curl"), process_productlist, dict())