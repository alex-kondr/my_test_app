from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://www.inside-digital.de/testberichte/'), process_revlist, dict())


def process_revlist(data, context, session):
    prods = data.xpath('//div[@class="td-pb-row article-list-content"]//div[@class="entry-title td-module-title"]//a')
    for prod in prods:
        title = prod.xpath("text()").string()
        url = prod.xpath("@href").string()
        if url:
            session.queue(Request(url), process_review, dict(url=url, title=title))

    nexturl = data.xpath("//div[@class='pager-button-next']//a/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2]
    product.category = data.xpath('//span[@class="td-bread-sep"]/following-sibling::span//text()').string()

    name = data.xpath('//h1[@class="entry-title td-page-title"]//span[not(@itemprop)]/text()').string()
    if name:
        product.name = name.split(' Testbericht')[0]

    imgs = data.xpath("//div[@class='td-post-content']//img/@src").strings()
    for img in imgs:
        product.add_property(type="image", value={'src': img})

    review = Review()
    review.url = product.url
    review.type = "user"
    review.title = context['title']
    review.ssid = product.ssid

    review_date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if review_date:
        review.date = review_date.split('T')[0]

    author_name = data.xpath('//span[@class="fn"]/a/text()').string()
    author_url = data.xpath('//span[@class="fn"]/a/@href').string()
    if author_name and author_url:
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))
    elif author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = len(data.xpath("(//div[@class='star-rating'])[1]//i[@class='fas fa-star full']"))
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//div[@class="post-excerpt"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//span[@id="pro"]/ancestor::h2/following-sibling::ul[1]/li')
    if not pros:
        pros = data.xpath('//p[.//strong[contains(., "Pros")]]/following-sibling::ul[1]/li')

    for pro in pros:
        pro = pro.xpath('.//text()').string()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[@id="contra"]/ancestor::h2/following-sibling::ul[1]/li')
    if not cons:
        cons = data.xpath('//p[.//strong[contains(., "Contras")]]/following-sibling::ul[1]/li')

    for con in cons:
        con = con.xpath('.//text()').string()
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h2[contains(@id, "fazit")]/following-sibling::p[1]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    # excerpt = data.xpath('//div[@class="td-post-content"]//*[not(descendant-or-self::script)]//text()').string(multiple=True)
    excerpt = data.xpath('//h2[contains(@id, "fazit")]/preceding::p[not(.//strong)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(@class or .//*[@class="td-page-meta"])]//text()[not(contains(., "Euro"))]').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    product.reviews.append(review)

    session.emit(product)

    # conclusion_set = data.xpath("//span[contains(@id, 'fazit')]/ancestor::h2/following-sibling::p//text()")
    # conclusion = ''
    # for concl in conclusion_set:
    #     conclusion += concl.string()
    #     excerpt = excerpt.replace(concl.string(), '')

    # after_conclusion = data.xpath("//span[contains(@id, 'fazit')]/ancestor::h2/following-sibling::h2/following-sibling::p//text()").string(multiple=True)
    # if not after_conclusion:
    #     after_conclusion = data.xpath("//span[contains(@id, 'fazit')]/ancestor::h2/following-sibling::h3//text()").string(multiple=True)

    # affiliate = data.xpath('//p[contains(@class, "affiliate")]//text()').string(multiple=True)
    # if affiliate:
    #     excerpt = excerpt.replace(affiliate, '')

    # if conclusion:
    #     if after_conclusion:
    #         conclusion = conclusion.replace(after_conclusion, '')
    #     if affiliate:
    #         conclusion = conclusion.replace(affiliate, '')
    #     review.properties.append(ReviewProperty(type='conclusion', value=conclusion))



