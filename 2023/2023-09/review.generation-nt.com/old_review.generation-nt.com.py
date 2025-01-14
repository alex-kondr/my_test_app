from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.generation-nt.com/dossiers.html'), process_productlist, {})


def process_productlist(data, context, session):
    prods = data.xpath("//div[@class='item-zone']")
    for prod in prods:
        url = prod.xpath(".//a[@class='item-title']/@href").string()
        title = prod.xpath(".//a[@class='item-title']//text()").string()
        session.queue(Request(url), process_review, dict(context, url=url, title=title))

    nexturl = data.xpath("(//div[@class='pagination']/span[@class='current']/following-sibling::span/a)[1]/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_productlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.ssid = context['url'].split('/')[-1].split('.html')[0].split('-')[-1]
    product.url = context['url']

    category = " "
    cats = data.xpath('//span[@itemprop="name"]//text()')
    for cat in cats:
        category += '|' + cat.string()
    product.category = category.split('Accueil|')[-1].split('Dossiers|')[-1]

    name = context['title']
    if 'Test : ' in name:
        name = name.replace('Test :', '', 1)
    if 'Test ' in name:
        name = name.replace('Test ', '', 1)
    product.name = name.split(':')[0]

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//div[@class='titleinfo']//time/@datetime").string().split('T')[0]

    authors = data.xpath("//div[@class='titleinfo']//a")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    summary = data.xpath('//span[@itemprop="description"]//text()').string(multiple=True)
    if not summary:
        summary = data.xpath('//div[@class="description"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    text = data.xpath('//div[@id="intelliTXT"]//h2')
    if text:
        text_con = data.xpath('(//div[@id="intelliTXT"]//h2)[last()]//text()').string()
        if text_con == 'Conclusion':
            conclusion = data.xpath('(//div[@id="intelliTXT"]//h2)[last()]//following-sibling::p//text()').string(multiple=True)
            review.add_property(type='conclusion', value=conclusion)

            excerpt = data.xpath('(//div[@id="intelliTXT"]//h2)[last()]//preceding-sibling::p//text()').string(multiple=True)
        else:
            excerpt = data.xpath('//div[@id="intelliTXT"]//text()').string(multiple=True)
    else:
        excerpt = data.xpath('//div[@id="intelliTXT"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    pros = data.xpath("//div[@class='more']/ul/li//text()")
    for pro in pros:
        pro = pro.string().replace('+', '').strip()
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath("//div[@class='less']/ul/li//text()")
    for con in cons:
        con = con.string().replace('- ', '').strip()
        if con:
            review.add_property(type='cons', value=con)

    product.reviews.append(review)
    session.emit(product)
