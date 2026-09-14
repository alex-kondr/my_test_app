from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=8000)]
    session.queue(Request("http://multiplayer.it/articoli/recensioni/"), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    for rev in data.xpath("//h3/a"):
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(url=url))

    next_url = data.xpath("//li[@class='page-item'][last()]/a/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    title = data.xpath("//h1//text()").string(multiple=True)

    product = Product()
    product.name = title.split(': ')[0].split(", ")[0]
    product.ssid = context['url'].split('/')[-1].split('.html')[0]
    product.url = context['url']

    category = data.xpath('//small[contains(text(), "Versione testata")]/following-sibling::b/text()').string()
    if category:
        category = "Games|" + category
    if not category:
        category = data.xpath("//span[@class='article__header__type-author']/a[1]//text()").string(multiple=True)
    product.category = category
    
    review = Review()
    review.title = title
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']
    review.date = data.xpath("//*[@id='_article_pub_date']//text()").string()
    
    author = data.xpath("//span[@class='article__header__type-author']/a[2]").first()
    if author:
        author_name = author.xpath(".//text()").string()
        author_url = author.xpath("@href").string()
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))
    
    grade_overall = data.xpath("(//p[contains(@class,'article__verdict__boxes__vote')])[1]//text()").string(multiple=True)
    if grade_overall and grade_overall != "S.V.":
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))
    
    pros = data.xpath("//div[contains(@class, 'article__pros-cons__pros')]/ul/li")
    for pro in pros:
        pro = pro.xpath(".//text()").string()
        if pro:
            pro = pro.replace('+ ', '').strip()
        if pro:
            review.add_property(type='pros', value=pro)
    
    cons = data.xpath("//div[contains(@class, 'article__pros-cons__cons')]/ul/li")
    for con in cons:
        con = con.xpath(".//text()").string()
        if con:
            con = con.replace('- ', '').strip()
        if con:
            review.add_property(type='cons', value=con)
    
    summary = data.xpath("//p[contains(@class, 'subtitle')]//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))
    
    conclusion = data.xpath("//p[contains(@class, 'article__verdict__description')]//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
    
    excerpt = data.xpath("//div[@class='article__content']//p//text()").string(multiple=True)
    if excerpt:
        if summary:
            excerpt = excerpt.replace(summary, '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))
    
        product.reviews.append(review)
        session.emit(product)
    