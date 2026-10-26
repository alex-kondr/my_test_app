from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://carseatblog.com/category/carseat-baby-gear-vehicle-reviews/'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//h2[contains(@class, "card__title")]/a')
    for rev in revs:
        title = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(title=title, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].split(' Review: ')[0].replace(' Review', '').strip()
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('-reviews', '')
    product.category = 'Car seats'

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//span[@class="meta-date"]/time/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    pros = data.xpath('(//h4[regexp:test(., "ADVANTAGES:", "i")]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//h4[regexp:test(., "DISADVANTAGES:", "i")]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//h4[regexp:test(., "THE BOTTOM LINE|Conclusion", "i")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        data.xpath('//p[strong[contains(., "Summary")]]/following-sibling::p[not(regexp:test(., "Pros:|Cons:"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "Who should shortlist it")]/following-sibling::p//text').string(multiple=True)

    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h4[regexp:test(., "THE BOTTOM LINE|Conclusion", "i")]/preceding-sibling::p[not((preceding::h4|preceding::p/span|preceding::p/strong)[regexp:test(., "ADVANTAGES|DISADVANTAGES|THE BOTTOM LINE|Pros:|Cons:|Summary")])]//text()[not(regexp:test(., "Pros:|Cons:|Summary|\(In fairness"))]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[contains(., "Who should shortlist it")]/preceding-sibling::p[not(@class)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="entry-content"]/p[not(@class)]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
