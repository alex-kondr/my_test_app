from agent import *
from models.products import *

debug = True

def process_revlist(data, context, session):
    for rev in data.xpath("//article/following-sibling::a[1]"):
        url = rev.xpath("@href").string()
        title = rev.xpath("@title").string()
        if url and title:
            session.queue(Request(url), process_review, dict(url=url, title=title))

    nexturl = data.xpath("//a[@rel='next']/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath("//span[@class='smaller normal']//preceding-sibling::text()").string()
    if not(product.name):
        product.name = context['title']
    product.url = context['url']
    product.ssid = get_url_parameter(data.xpath("//link[@rel='shortlink']/@href").string(), 'p')
    product.category = data.xpath("//div[regexp:test(@class,'breadcrumbs')]/descendant::a[position()>1]/text()").join('|') or 'unknown'
    product.manufacturer = data.xpath("//span[contains(text(), 'Hersteller')]//following-sibling::text()").string()
   
    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date_author = data.xpath("//span[@class='stars']//following-sibling::text()").string(multiple=True) or 'unknown'
    if date_author:
        date = ''
        author = ''
        if 'am' in date_author:
            date = date_author.split('am')[-1]
            author = date_author.split('von')[-1].split('am')[0]
        else:
            author = date_author.split('von')[-1]     
        if author:
            review.authors.append(Person(name=author, ssid=author))
        if date:
            review.date = date

    score = 0
    for grade in data.xpath("//span[@class='stars']//span[@class='fa fa-star']"):
        if grade:
           score += 1
    if score:
        review.grades.append(Grade(name='Wertung', type='overall', value=float(score), best=5.0))
    else:
        review.grades.append(Grade(name='Wertung', type='overall', value=0.0, best=5.0))

    summary = data.xpath("//div[@id='wertung']/following::body[1]//p[@itemprop='description']//text()").string(multiple=True)
    if not(summary):
        summary = data.xpath("//div[@itemprop='reviewBody']/p//text()").string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath("//p[@class='article_teaser']//text()").string()
    if not(excerpt):
        excerpt = data.xpath("//p[@id='wasistes']/following-sibling::p[not(preceding-sibling::h3)]//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

    conclusion = data.xpath("//div[@class='tb_fazit']//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    for pro in data.xpath("//ul[@class='pro']/li"):
        line = pro.xpath("descendant::text()").string(multiple=True)
        if line:
            review.add_property(type='pros', value=line)

    for con in data.xpath("//ul[@class='contra']/li"):
        line = con.xpath("descendant::text()").string(multiple=True)
        if line:
            review.add_property(type='cons', value=line)

    if conclusion or excerpt or summary:
        product.reviews.append(review)
        session.emit(product)


def run(context, session):
    session.browser.agent = "Mozilla/6.0"
    session.queue(Request('http://www.delamar.de/testberichte/'), process_revlist, {})