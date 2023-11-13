from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.chargerharbor.com/',  use='curl'), process_frontpage, dict(page=1))


def process_frontpage(data, context, session):
    categs = data.xpath("//ul[@id='menu-primary-menu']//a[contains(., 'Product Reviews')]/following-sibling::ul/li")
    for cat in categs:
        name1 = cat.xpath("a/text()").string()
        url1 = cat.xpath('a/@href').string()

        subcats = cat.xpath("ul/li")
        for subcat in subcats:
            name2 = name1 + '|' + subcat.xpath('a/text()').string()
            url2 = subcat.xpath('a/@href').string()

            subcats2 = subcat.xpath("ul/li")
            for subcat2 in subcats2:
                name3 = name2 + '|' + subcat2.xpath('a/text()').string()
                url3 = subcat2.xpath('a/@href').string()

                session.queue(Request(url3, use='curl'), process_prodlist, dict(context, cat=name3, cat_url=url3))
            session.queue(Request(url2, use='curl'), process_prodlist, dict(context, cat=name2, cat_url=url2))
        session.queue(Request(url1, use='curl'), process_prodlist, dict(context, cat=name1, cat_url=url1))


def process_prodlist(data, context, session):
    prods = data.xpath("//h2[@class='entry-title']/a")
    for prod in prods:
        url = prod.xpath("@href").string()
        title = prod.xpath("text()").string()
        session.queue(Request(url, use='curl'), process_review, dict(context, url=url, title=title))

    if len(prods) >= 10:
        page = context.get('page', 1) + 1
        nexturl = context['cat_url'] + 'page/' + str(page)
        session.queue(Request(nexturl, use='curl'), process_prodlist, dict(context, page=page))


def process_review(data, context, session):
    product = Product()
    product.ssid = data.xpath("//article/@id").string().split('-')[1]
    product.url = context['url']
    product.name = data.xpath("//div[@class='cwpr-review-top cwpr_clearfix']/h2[@class='cwp-item']/text()").string()
    product.category = context['cat']

    review = Review()
    review.title = context['title']
    review.type = 'user'
    review.url = context['url']
    review.ssid = product.ssid

    user = data.xpath("//span[@class='author vcard']/a//text()").string()
    user_url = data.xpath("//span[@class='author vcard']/a/@href").string()
    if user:
        review.authors.append(Person(name=user, ssid=user_url, profile_url=user_url))

    pros = data.xpath("//div[@class='review-wu-right']/div[@class='pros']//ul/li/text()")
    for pro in pros:
        review.add_property(type='pros', value=pro.string())

    cons = data.xpath("//div[@class='review-wu-right']/div[@class='cons']//ul/li/text()")
    for con in cons:
        review.add_property(type='cons', value=con.string())

    grades = data.xpath('//div[@class="rev-option"]')
    for grade in grades:
        name = grade.xpath('.//h3//text()').string()
        value = grade.xpath('div/span[3]/text()').string(multiple=True).split('/')
        review.grades.append(Grade(name=name, value=value[0], best=value[1]))

    grade_overall = data.xpath("//div[@class='review-wu-grade']//span/text()").string()
    if grade_overall:
        review.grades.append(Grade(value=grade_overall, best=10, type="overall"))

    excerpt = data.xpath("//div[contains(@class,'affiliate-button')]/parent::node()/following-sibling::*[self::p|self::h1|self::h2]//text()").string(multiple=True)
    summary = data.xpath("//h1[contains(., 'Summary')]/following-sibling::p//text()").string(multiple=True)
    conclusion = data.xpath("//h1[contains(., 'Conclusion')]/following-sibling::p//text()").string(multiple=True)

    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
        summary = summary.replace(conclusion, '')
        excerpt = excerpt.replace(conclusion, '')
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))
        excerpt = excerpt.replace(summary, '')
    if excerpt:
        excerpt = excerpt.split(' Specs of the ')[0]
        excerpt = excerpt.replace(' Conclusion: ', '')
        excerpt = excerpt.replace(' Summary:: ', '')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if conclusion or summary or excerpt:
        product.reviews.append(review)
        session.emit(product)
