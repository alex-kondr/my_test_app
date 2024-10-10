from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('http://digiarena.e15.cz/testy'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//a[@class='ar-title gtm-track-t'][not(@onclick)]")
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()
        session.queue(Request(url), process_review, dict(name=name, url=url))

    next_page = data.xpath('//a[@class="next pagging"]/@href').string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]

    product.name = context['name'].replace(' (test)', '').replace(' [test]', '').replace('Recenze: ', '')
    if ' – ' in product.name:
        product.name = product.name.split(' – ')[0]

    product.category = data.xpath("//p[@class='ar-tags ar-tags-top']/span[last()-1]/a/text()").string()
    if product.category == 'DIGIarena.cz':
        product.category = data.xpath("//p[@class='ar-tags ar-tags-top']/span[last()]/a/text()").string()

    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath("//span[@class='ar-date']/text()").string()

    author = data.xpath("//span[@class='ar-author']/a").first()
    if author:
        name = author.xpath("text()").string()
        url = author.xpath("@href").string()
        review.authors.append(Person(name=name, ssid=name, profile_url=url))

    grade = data.xpath("//span[@class='bigger']/text()").string()
    if grade:
        review.grades.append(Grade(type='overall', value=int(grade), best=10))

    summary = data.xpath("//div[@class='ar-annotation']/text()").string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath("//div[@class='rating-plus rating-box']//li/text()")
    if not pros:
        pros = data.xpath("//*[contains(.,'Plusy:')]/following-sibling::ul[1]//li/text()")
    for pro in pros:
        value = pro.string()
        review.add_property(type="pros", value=value)

    cons = data.xpath("//div[@class='rating-minus rating-box']//li/text()")
    if not cons:
        cons = data.xpath("//*[contains(.,'nusy:')]/following-sibling::ul[1]//li/text()")
    for con in cons:
        value = con.string()
        review.add_property(type="cons", value=value)

    next_page = data.xpath("//a[@data-ga='Navigace;NextChapter']/@href").string()
    if next_page:
        next_page = next_page.split('#')[0]
        session.do(Request(next_page), process_lastpage, dict(review=review, pros=pros, url=next_page))

    excerpt = data.xpath("//div[@class='bodyPart']/p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[contains(@class,'ar-inquiry-holder')]/p//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)


def process_lastpage(data, context, session):
    review = context["review"]
    page = context.get("page", 2)

    title = data.xpath("//h1/text()").string()
    review.add_property(type="pages", value=dict(url=context["url"], title=title+' - Page '+str(page)))

    if not context['pros']:
        pros = data.xpath("//div[@class='rating-plus rating-box']//li/text()")
        if pros:
            context['pros'] = pros
        if not pros:
            pros = data.xpath("//*[contains(.,'Plusy:')]/following-sibling::ul[1]//li/text()")
        for pro in pros:
            value = pro.string()
            review.add_property(type="pros", value=value)

        cons = data.xpath("//div[@class='rating-minus rating-box']//li/text()")
        if not cons:
            cons = data.xpath("//*[contains(.,'nusy:')]/following-sibling::ul[1]//li/text()")
        for con in cons:
            value = con.string()
            review.add_property(type="cons", value=value)

    next_page = data.xpath("//a[@data-ga='Navigace;NextChapter']/@href").string()
    if next_page:
        next_page = next_page.split('#')[0]

        session.do(Request(next_page), process_lastpage, dict(context, url=next_page, page=page+1))
        return

    conclusion = data.xpath("//div[@class='bodyPart']/p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[contains(@class,'ar-inquiry-holder')]/p//text()").string(multiple=True)
        review.add_property(type='conclusion', value=conclusion)
