from agent import *
from models.products import *
import simplejson


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=3000)]
    session.queue(Request('https://pt.ign.com/article/review'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="m"]')
    for rev in revs:
        date = rev.xpath('.//time/@datetime').string()
        title = rev.xpath('h3//a/text()').string()
        url = rev.xpath('h3//a/@href').string()
        session.queue(Request(url), process_product, dict(title=title, date=date, url=url))

    next_url = data.xpath('//link[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_product(data, context, session):
    product = Product()
    product.name = context['title'].replace('- Análise', '').replace('-Análise', '').replace('Análise -', '').replace('Análise-', '').replace('Análise', '').strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1]
    product.manufacturer = data.xpath('//span[@class="txt"]/text()').string()

    platforms = data.xpath('//body[.//@class="platform" and not(.//div)]/preceding-sibling::head[1]/title/text()').strings()
    if platforms:
        product.category = '/'.join(platforms)

    prod_json = data.xpath('//script[@type="application/ld+json" and contains(., "description")]/text()').string()
    if prod_json:
        prod_json = simplejson.loads(prod_json)

        if product.category:
            product.category += '|' + prod_json.get('@type')
        else:
            product.category = prod_json.get('@type')

        if not product.manufacturer:
            product.manufacturer = prod_json.get('brand', {}).get('name')

        sku = prod_json.get('sku')
        if sku:
            product.sku = str(sku)

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    if context.get('date'):
        review.date = context['date'].split('T')[0]

    author = data.xpath('//div[@class="author-names"]//a[@class="url"]/text()').string()
    author_url = data.xpath('//div[@class="author-names"]//a[@class="url"]/@href').string()
    if author and author_url:
        review.authors.append(Person(name=author, ssid=author, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//h3[@id="id_deck"]/text()').string()
    if summary:
        review.add_property(type='summary', value=summary)

    context['product'] = product
    context['review'] = review
    process_review(data, context, session)


def process_review(data, context, session):
    review = context['review']

    grade_overall = data.xpath('//div[@class="review"]//span[@class="side-wrapper side-wrapper hexagon-content"]/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//ul[contains(@id, "pros")]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[contains(@id, "pros")]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        review.add_property(type='cons', value=con)

    conclusion = data.xpath('(//h3[contains(., "Veredito")]/following-sibling::p)[1]//text()').string(multiple=True)
    if conclusion:
        conclusion_ = conclusion.split('<a')
        if len(conclusion_) > 1:
            conclusion = conclusion_[0] + conclusion_[1].split('>')[-1]
        conclusion = conclusion.replace('</A>', '').replace('</a>', '').replace('[poilib element=\"accentDivider\"]', '').replace('<em>', '').replace('</em>', '')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[@itemprop="articleBody"]//text()').string(multiple=True)
    if excerpt:
        context['excerpt'] = context.get('excerpt', '') + ' ' + excerpt

    next_page = data.xpath('//a[contains(@class, "page p") and contains(@href, "?p=")]/@href').string()
    page = context.get('page', 1)
    if next_page and int(next_page.split('=')[-1]) > page:
        title = review.title + ' - Pagina ' + str(page)
        review.add_property(type='pages', value=dict(title=title, url=data.response_url))
        session.do(Request(next_page), process_review, dict(context, review=review, page=page + 1))

    elif context.get('excerpt'):
        if context.get('page'):
            title = review.title + ' - Pagina ' + str(context['page'])
            review.add_property(type='pages', value=dict(title=title, url=data.response_url))

        review.add_property(type='excerpt', value=context['excerpt'].strip())

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
