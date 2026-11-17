from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers=[SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.bit-tech.net/reviews/?page=1'), process_revlist, {})


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath("//div[@class='articleinfo']/a")
    for rev in revs:
        title = rev.xpath(".//text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))
    
    nexturl = data.xpath("//div[@id='page_navigation']/a[contains(.,'Next')]/@href").string()
    if nexturl:
        session.queue(Request(nexturl), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    title = context['title'] or data.xpath("//h1[@class='heading']//text()").string()
    if not title:
        return # Empty article, sometimes happens

    product = Product()
    product.name = title.replace('Review', '')
    product.ssid = context['url'].split('/')[-3]
    product.url = context['url']
    product.manufacturer = data.xpath("//div[@id='page_body']/p[contains(.,'Manufacturer')]/text()[not(self::strong)]").string()
    product.category = 'Reviews'
    
    review = Review()
    review.title = title
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//p[@class='datetime']//text()").string().split(' | ')[0]
    
    authors = data.xpath("//p[@class='author']/a")
    for author in authors:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))

    pages = data.xpath("(//select[@id='select_pages'])[1]/option")
    for page in pages:
        page_url = 'https://www.bit-tech.net' + page.xpath("@value").string().strip()
        page_title = page.xpath(".//text()").string().strip()
        review.properties.append(ReviewProperty(type='pages', value={'url': page_url, 'title': page_title}))
    
    if pages:
        last_url = 'https://www.bit-tech.net' + pages.last().xpath("@value").string().strip()
        session.do(Request(last_url), process_review_last, dict(context, product=product, review=review))
    else:
        context['product'] = product
        context['review'] = review
        process_review_last(data: Response, context: dict[str, str], session: Session)
    
    
def process_review_last(data: Response, context: dict[str, str], session: Session):
    product = context['product']
    review = context['review']
    
    excerpt = data.xpath("//div[@id='page_body']//p//text()").string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[@id='page_body']//text()").string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
    
    pros = data.xpath("//div[@id='page_body']/p[contains(.,'The Good')]/following-sibling::ul[1]/li//text()")
    for pro in pros:
        pro = pro.string().replace('+', '').strip()
        review.add_property(type='pros', value=pro)
    
    cons = data.xpath("//div[@id='page_body']/p[contains(.,'The Not So Good')]/following-sibling::ul[1]/li//text()")
    for con in cons:
        con = con.string().replace('- ', '').strip()
        review.add_property(type='cons', value=con)
    
    product.reviews.append(review)
    session.emit(product)