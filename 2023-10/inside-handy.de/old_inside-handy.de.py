from agent import *
from models.products import *


def process_category(data, context, session):
    for prod in data.xpath('//div[@class="td-pb-row article-list-content"]//div[@class="entry-title td-module-title"]'):
        name = prod.xpath(".//a/text()").string()
        url = prod.xpath(".//a/@href").string()
        if url:
            session.queue(Request(url, use='curl'), process_product, dict(url=url, name=name))

    nexturl = data.xpath("//div[@class='pager-button-next']//a/@href").string()
    if nexturl:
        session.queue(Request(nexturl, use='curl'), process_category, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = data.xpath('//span[@class="td-bread-sep"]/following-sibling::span//text()').string()

    review = Review()
    review.url = product.url
    review.type = "user"

    review_date = data.xpath("//time[@class='entry-date td-module-date']/@datetime")
    if review_date:
        review.date = review_date.string().split('T')[0]

    author_name = data.xpath("//div[@class='author-wrapper']//text()").string(multiple=True)
    author_url = data.xpath("//div[@class='author-wrapper']//a/@href").string()
    if author_name and author_url:
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    summary = data.xpath('//div[@class="post-excerpt"]//text()').string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath('//div[@class="td-post-content"]//*[not(descendant-or-self::script)]//text()').string(multiple=True)

    conclusion_set = data.xpath("//span[contains(@id, 'fazit')]/ancestor::h2/following-sibling::p//text()")
    conclusion = ''
    for concl in conclusion_set:
        conclusion += concl.string()
        excerpt = excerpt.replace(concl.string(), '')

    after_conclusion = data.xpath("//span[contains(@id, 'fazit')]/ancestor::h2/following-sibling::h2/following-sibling::p//text()").string(multiple=True)
    if not after_conclusion:
        after_conclusion = data.xpath("//span[contains(@id, 'fazit')]/ancestor::h2/following-sibling::h3//text()").string(multiple=True)

    affiliate = data.xpath('//p[contains(@class, "affiliate")]//text()').string(multiple=True)
    if affiliate:
        excerpt = excerpt.replace(affiliate, '')

    if conclusion:
        if after_conclusion:
            conclusion = conclusion.replace(after_conclusion, '')
        if affiliate:
            conclusion = conclusion.replace(affiliate, '')
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    if data.xpath('//span[@id="pro"]/ancestor::h2'):
        pros = data.xpath('//span[@id="pro"]/ancestor::h2/following-sibling::ul[1]/li//text()')
        for pro in pros:
            excerpt = excerpt.replace(pro.string(), '')
            review.add_property(type='pros', value=pro.string())

    if data.xpath('//span[@id="contra"]/ancestor::h2'):
        cons = data.xpath('//span[@id="contra"]/ancestor::h2/following-sibling::ul[1]/li//text()')
        for con in cons:
            excerpt = excerpt.replace(con.string(), '')
            review.add_property(type='cons', value=con.string())

    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if author_name:
        review.ssid = product.ssid + '-' + review.date + '-' + author_name
    else:
        review.ssid = '%s-%s' % (product.ssid, hashlib.md5(review.date + excerpt).hexdigest())

    for img in data.xpath("//div[@class='td-post-content']//img"):
        src = img.xpath("@src").string()
        if src:
            product.properties.append(ProductProperty(type="image", value={'src': src}))

    grade_overall = len(data.xpath("(//div[@class='star-rating'])[1]//i[@class='fas fa-star full']"))
    if grade_overall:
        review.grades.append(Grade(type='overall', value=int(grade_overall), best=5))

    product.reviews.append(review)
    session.emit(product)


def run(context, session):
    session.queue(Request('https://www.inside-digital.de/testberichte/', use='curl'), process_category, dict())
