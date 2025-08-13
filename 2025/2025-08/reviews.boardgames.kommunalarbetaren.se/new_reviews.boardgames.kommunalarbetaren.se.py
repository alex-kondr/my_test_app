from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('https://arbetet.se/2013/12/12/10-spelnyheter-for-hela-familjen/'), process_prodlist, dict(url='https://arbetet.se/2013/12/12/10-spelnyheter-for-hela-familjen/'))
    session.queue(Request('https://arbetet.se/2014/12/05/sa-bra-ar-arets-spelnyheter/'), process_prodlist, dict(url='https://arbetet.se/2014/12/05/sa-bra-ar-arets-spelnyheter/'))
    session.queue(Request('https://arbetet.se/2012/12/18/atta-spelnyheter-att-lira-i-jul/'), process_prodlist, dict(url='https://arbetet.se/2012/12/18/atta-spelnyheter-att-lira-i-jul/'))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="Body"]/h2')
    if not prods:
        prods = data.xpath('//div[@class="Body"]/p')

    for i, prod in enumerate(prods, start=1):
        product = Product()
        product.name = prod.xpath('u/strong/text()').string() or prod.xpath('.//text()').string(multiple=True)
        product.url = context['url']
        product.ssid = product.url.split('/')[-2]
        product.category = 'Board Games'

        review = Review()
        review.type = 'pro'
        review.title = product.name
        review.url = product.url
        review.ssid = product.ssid

        grade_overall = prod.xpath('strong[contains(., "Betyg:")]/following-sibling::text()[normalize-space(.)][1]').string() or prod.xpath('following-sibling::p[count(preceding-sibling::h2)={i}]/strong[contains(., "Betyg:")]/following-sibling::text()[normalize-space(.)][1]|following-sibling::p[count(preceding-sibling::h2)={i}]/strong[contains(., "Betyg:")]/following-sibling::img/@src|following-sibling::p[count(preceding-sibling::h2)={i}]/strong[contains(., "Betyg:")]/img/@src'.format(i=i)).string()
        if grade_overall:
            grade_overall = grade_overall.replace('.jpg', '').split('betyg')[-1].split('_')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        pros = prod.xpath('strong[contains(., "Plus:")]/following-sibling::text()[normalize-space(.)][1]').string() or prod.xpath('following-sibling::p[count(preceding-sibling::h2)={}]/strong[contains(., "Plus:")]/following-sibling::text()[normalize-space(.)][1]'.format(i)).string()
        if pros:
            pros = pros.strip(' +-*.:;•,–')
            if len(pros) > 1:
                review.add_property(type='pros', value=pros)

        cons = prod.xpath('strong[contains(., "Minus:")]/following-sibling::text()[normalize-space(.)][1]').string() or prod.xpath('following-sibling::p[count(preceding-sibling::h2)={}]/strong[contains(., "Minus:")]/following-sibling::text()[normalize-space(.)][1]'.format(i)).string()
        if cons:
            cons = cons.strip(' +-*.:;•,–')
            if len(cons) > 1:
                review.add_property(type='cons', value=cons)

        summary = prod.xpath('strong[contains(., "Går ut på:")]/following-sibling::text()[normalize-space(.)][1]').string(multiple=True) or prod.xpath('following-sibling::p[count(preceding-sibling::h2)={}]/strong[contains(., "Går ut på:")]/following-sibling::text()[normalize-space(.)][1]'.format(i)).string()
        if summary:
            review.add_property(type='summary', value=summary)

        excerpt = prod.xpath('strong[contains(., "Övrigt:")]/following-sibling::text()[normalize-space(.)][1]').string(multiple=True) or prod.xpath('following-sibling::p[count(preceding-sibling::h2)={}]/strong[contains(., "Övrigt:")]/following-sibling::text()[normalize-space(.)][1]'.format(i)).string()
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
