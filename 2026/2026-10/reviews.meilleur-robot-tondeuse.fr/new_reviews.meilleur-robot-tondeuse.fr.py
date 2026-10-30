from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.meilleur-robot-tondeuse.fr/avis', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    brands = data.xpath('//div[@class="prose"]/h2')
    for brand in brands:
        name = brand.xpath('text()').string()

        prods = brand.xpath('(following-sibling::ul)[1]/li/a/@href')
        for prod in prods:
            url = prod.string()
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(brand=name, url=url))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = data.xpath('//div[@class="pcard-title"]/h3/text()').string()
    product.ssid = context['url'].split('/')[-2].replace('-avis', '')
    product.category = 'Tondeuses à gazon robotisées'
    product.manufacturer = context['brand']

    url = data.xpath('//a[contains(., "sur Amazon.fr")]/@href[contains(., "/dp/")]').string()
    if url:
        product.url = url

        mpn = url.split('?')[0].split('/')[-1]
        if mpn:
            product.add_property(type='id.manufacturer', value=mpn)
    else:
        product.url = context['url']

    review = Review()
    review.type = 'pro'
    review.title = data.xpath('//h1/text()').string()
    review.url = context['url']
    review.ssid = product.ssid
    review.date = data.xpath('//p[@class="meta"]/time/@datetime').string()

    # all author 'la rédaction'

    grade_overall = data.xpath('//div[@class="pcard-body"]//span[@class="score"]/b/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.replace(',', '.'))
        if grade_overall > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('//ul[@class="pros"]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('//ul[@class="cons"]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//div[@class="prose"]/p[count(preceding-sibling::h2)=1]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[article[@class="main"]]/p[@class="lead"]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
