from agent import *
from models.products import *


def run(context, session):
    session.browser.use_new_parser = True
    session.queue(Request('http://www.all-nintendo.com/tests'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='hgroup']/p[@class='title']/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_page = data.xpath("//span[@class='pages']/strong[@class='on']/following-sibling::a[1]/@href").string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' - ')[0].split(": ")[0]
    product.ssid = context['url'].split('/')[-1].split('.html')[0]
    product.url = context['url']

    if 'Test sur' in context['title']:
        product.category = 'Games|' + context['title'].split('Test sur')[1].strip()
    else:
        product.category = 'Games'

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("(//section[@class='framenav']/div)[2]//text()").string(multiple=True).split('le')[1].split(' - ')[0]

    author = data.xpath("(//section[@class='framenav']/div)[2]//text()").string(multiple=True).split('par')[1].split(',')[0]
    if author and author != ' ':
        review.authors.append(Person(name=author, ssid=author))

    grade = data.xpath("//strong[contains(.,'Note')]//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//p[contains(.,'Note')]//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//strong[contains(.,'/20')]//text()").string(multiple=True)
    if grade:
        if '/' in grade:
            if ' ' in grade:
                grade_value = grade.split('/')[0].split(' ')[-1]
            else:
                grade_value = grade.split('/')[0]
            grade_best = grade.split('/')[1]
            if grade_value.isdigit() and grade_best.isdigit():
                review.grades.append(Grade(type='overall', value=int(grade_value), best=int(grade_best)))

    pros = data.xpath("//strong[contains(.,'+')]/parent::p/text()")
    if not pros:
        pros = data.xpath("//strong[contains(.,'+')]/parent::p/following-sibling::p[1]/text()")
    for pro in pros:
        review.add_property(type='pros', value=pro.string())

    cons = data.xpath("//strong[contains(.,'-')]/parent::p/text()")
    if not cons:
        cons = data.xpath("//strong[contains(.,'-')]/parent::p/following-sibling::p[1]/text()")
    for con in cons:
        review.add_property(type='cons', value=con.string())

    conclusion = data.xpath("//div[@class='tabWrapper']//p[contains(.,'Conclusion')]/following-sibling::p[1]//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath("//div[@class='tabWrapper']//span/p//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        if '. Note : ' in excerpt:
            excerpt = excerpt.split('. Note : ')[0]
        if '. Note: ' in excerpt:
            excerpt = excerpt.split('. Note: ')[0]
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)
        session.emit(product)
