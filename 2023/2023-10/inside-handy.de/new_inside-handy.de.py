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

    next_url = data.xpath("//div[@class='pager-button-next']//a/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-2]
    product.category = 'Handys'

    product.url = data.xpath('//a[contains(text(), "Amazon ansehen!")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.name = data.xpath('//h1[@class="entry-title td-page-title"]//span[not(@itemprop)]/text()').string()
    if product.name:
        product.name = product.name.split('Testbericht')[0].split('PureView')[0].strip()
    else:
        product.name = context['title']

    product.manufacturer = data.xpath('(//span[@class="td-bread-sep"]/following-sibling::span//span[@itemprop="name"])[2]/text()').string()

    imgs = data.xpath("//div[@class='td-post-content']//img/@src").strings()
    for img in imgs:
        product.add_property(type="image", value={'src': img})

    review = Review()
    review.url = context['url']
    review.type = "pro"
    review.title = context['title']
    review.ssid = product.ssid

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author_name = data.xpath('//span[@class="fn"]/a/text()').string()
    author_url = data.xpath('//span[@class="fn"]/a/@href').string()
    if author_name and author_url:
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))
    elif author_name:
        review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath('//p[contains(., "Gesamtwertung:")]//text()').string(multiple=True)
    if not grade_overall:
        grade_overall = data.xpath('count((//div[@class="star-rating"])[1]//i[@class="fas fa-star full"])')
    if grade_overall:
        grade_overall = str(grade_overall).split(':')[-1].split('von')[0].split('/')[0].replace(',', '.').replace('Sterne', '').strip()
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//div[@class="post-excerpt"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath('//span[@id="pro"]/ancestor::h2/following-sibling::ul[1]/li[not(.//a)]')
    if not pros:
        pros = data.xpath('//p[starts-with(., "Pro")]/following-sibling::ul[1]/li[not(.//a)]')
    if not pros:
        pros = data.xpath('//h3[starts-with(., "Pro")]/following-sibling::ul[1]/li[not(.//a)]')

    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    pros = data.xpath('//h3[starts-with(., "Pro")]/following-sibling::p[1][contains(., "•")]//text()').strings()
    for pro in pros:
        pro = pro.replace('•', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//span[@id="contra"]/ancestor::h2/following-sibling::ul[1]/li[not(.//a)]')
    if not cons:
        cons = data.xpath('//p[starts-with(., "Contra")]/following-sibling::ul[1]/li[not(.//a)]')
    if not cons:
        cons = data.xpath('//h3[starts-with(., "Contra")]/following-sibling::ul[1]/li[not(.//a)]')

    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    cons = data.xpath('//h3[starts-with(., "Contra")]/following-sibling::p[contains(., "•")]//text()').strings()
    for con in cons:
        con = con.replace('•', '').strip()
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h2[contains(@id, "fazit")]/following-sibling::p[not(contains(., "Pros ") or contains(., "Pro ") or contains(., "Contras") or contains(., "•"))]|//h2[contains(@id, "fazit")]/following-sibling::h2)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//h2[starts-with(., "Fazit")]/following-sibling::p[not(contains(., "Pros ") or contains(., "Pro ") or contains(., "Contras") or .//strong or contains(., "•"))]|//h2[starts-with(., "Fazit")]/following-sibling::h2)//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('(//p[.//strong[starts-with(., "Fazit")]]/following-sibling::p[not(contains(., "Pros ") or contains(., "Pro ") or contains(., "Contras") or .//strong or contains(., "•"))]|//p[.//strong[starts-with(., "Fazit")]]/following-sibling::h2)//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.split('Alternativen')[0].replace('Preis Leistung', '').replace('Preis-Leistung', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(@id, "fazit")]/preceding::p[not(.//strong)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//h2[starts-with(., "Fazit")]/preceding::p[not(.//strong)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//strong[starts-with(., "Fazit")]]/preceding-sibling::p[not(.//strong or contains(., "•"))]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//body//p[not(@class or .//*[@class="td-page-meta"] or contains(., "•") or starts-with(., "Pro") or starts-with(., "Contra"))]//text()[not(contains(., "Euro"))]').string(multiple=True)

    if excerpt and len(excerpt) > 45:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
