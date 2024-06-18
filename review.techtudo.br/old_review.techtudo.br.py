from agent import *
from models.products import *


def process_productlist(data, context, session):
    for rev in data.xpath("//div[@class='feed-post-body']"):
        prName = rev.xpath("descendant::a[regexp:test(@class,'feed-post-link')]//text()").string(multiple=True)
        if prName:
            prName = prName.replace("Review ", "")
        prUrl = rev.xpath("descendant::a[regexp:test(@class,'feed-post-link')]/@href").string(multiple=True)
        catName = rev.xpath("descendant::span[@class='feed-post-metadata-section']//text()").string()
        if prName and prUrl and catName:
            if prUrl.count('.ghtml'): 
                session.queue(Request(prUrl), process_review_ghtml, dict(context, prUrl=prUrl, prName=prName, catName=catName))
            else:
                session.queue(Request(prUrl), process_review_html, dict(context, prUrl=prUrl, prName=prName, catName=catName))

    next = data.xpath("//div[@class='load-more gui-color-primary-bg']/descendant::a/@href").string()
    if next:
        session.queue(Request(next), process_productlist, dict(context))
     

def process_review_html(data, context, session):
    product = Product()
    product.name = context['prName']
    product.category = context['catName']
    product.url = context['prUrl']
    product.ssid = re_search_once(r'review\/(.*)\.', product.url)

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    product.reviews.append(review)

    date = data.xpath('//time[@class="data"]/@content').string(multiple=True)
    if date:
        date = date.split("T")[0]
        review.date = time.strftime("%Y-%m-%d", time.strptime(date, "%Y-%m-%d"))

    author = data.xpath('//a[@class="nome"]/text()').string()
    authUrl = data.xpath('//a[@class="nome"]/@href').string()

    if author and authUrl:
        review.authors.append(Person(name=author, ssid=author, url=authUrl))

    excerpt = data.xpath("//div[@class='corpo-conteudo']/p[string-length(normalize-space(.))>150][1]//text()").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    conclusion = data.xpath("//node()[regexp:test(name(),'p|h2')][regexp:test(normalize-space(.),'Conclusão')]/following-sibling::p[1]//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    cons = data.xpath("//h2[@class='review-nota-tt-titulo' and normalize-space(.//text())='Contras']/following-sibling::ul[1]/li//text()").strings()
    pros = data.xpath("//h2[@class='review-nota-tt-titulo' and normalize-space(.//text())='Prós']/following-sibling::ul[1]/li//text()").strings()
    cons = [f.strip().strip('+-:.;* ') for f in cons if f.strip()]
    pros = [f.strip().strip('+-:.;* ') for f in pros if f.strip()]

    if pros:
        review.properties.append(ReviewProperty(name="Pros", type="pros", value=pros))
    if cons :
        review.properties.append(ReviewProperty(name="Cons", type="cons", value=cons))

    grade = data.xpath('//dd[contains(@class,"nota-tt-valor") and @itemprop="ratingValue"]//text()').string()

    if grade:
        review.grades.append(Grade(value=float(grade), best = 10, worst=0, name = 'Grade', type='overall'))

    for scores in data.xpath("//dl[@class='notas-grafico-notas-mobile']/dt[@class='nota-label']"):
        rate = scores.xpath("following-sibling::dd[contains(@class,'nota-barra')][1]//text()").string()
        name = scores.xpath("descendant::span[@class='logo-mobile']//text()").string()
        if rate and name:
            review.grades.append(Grade(name=name, value=float(rate), best = 10, worst=0))

    session.emit(product)


def process_review_ghtml(data, context, session):
    product = Product()
    product.name = context['prName']
    product.category = context['catName']
    product.url = context['prUrl']
    product.ssid = re_search_once(r'review\/(.*)\.', product.url)

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid
    product.reviews.append(review)

    date = data.xpath('//time[@itemprop="datePublished"]/@datetime').string(multiple=True)
    if date:
        date = date.split("T")[0]
        review.date = time.strftime("%Y-%m-%d", time.strptime(date, "%Y-%m-%d"))

    author = data.xpath('//div[@class="content-publication-data__text"]/p[@class="content-publication-data__from"]//text()').string()
    if author:
        author = author.split('Por ')[-1].split(',')[0]
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "mc-column")]/p[contains(@class, "theme-color-primary-first-letter") and string-length(normalize-space(.))>150]//text()').string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    conclusion = data.xpath('//div[contains(@class, "mc-column")][descendant::h2[contains(normalize-space(.),"Conclusão")]]/following::p[@class="content-text__container"][string-length(normalize-space(.))>150][1]//text()').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    grade = data.xpath('//svg[@class="review__circle-score"]/parent::span/text()').string(multiple=True)

    if grade:
        review.grades.append(Grade(value=float(grade), best = 10, worst=0, name = 'Grade', type='overall'))

    for scores in data.xpath('//div[@class="review__barrinhas"]/div[@class="review__attribute"]'):
        rate = scores.xpath('div[@class="review__attribute-score"]//text()').string()
        name = scores.xpath('div[@class="review__attribute-name"]//text()').string()
        if rate and name:
            review.grades.append(Grade(name=name, value=float(rate), best = 10, worst=0))

    session.emit(product)



def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request('http://www.techtudo.com.br/reviews/'), process_productlist, {})
