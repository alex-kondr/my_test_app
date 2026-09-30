from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request('https://www.cubed3.com/'), process_category, {})


def process_category(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//li[contains(@class,"drawer homepage_menu_")]//a[contains(.,"Reviews") and not(contains(.,"Latest Reviews")) and not(contains(.,"All Tech Reviews"))]')
    for cat in cats:
        name = cat.xpath('text()').string().replace(' Reviews','')
        url = cat.xpath('@href').string()
        if url:
            session.queue(Request(url, force_charset='utf-8'), process_revlist, dict(context, cat=name))


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="wrapper blog-posts"]//div')
    for rev in revs:
        name = rev.xpath('h3//text()').string()
        rev_url = rev.xpath('h3/a/@href').string()
        author = rev.xpath('p/span/text()').string()
        datetime = rev.xpath('.//time/@datetime').string().split("T")[0]
        if rev_url:
            session.queue(Request(rev_url, force_charset='utf-8'), process_review, dict(context, rev_url=rev_url, name=name, author=author, datetime=datetime))

    next_url = data.xpath('//a[@class="next page-numbers"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name'].replace('Reviews', '').replace('Review', '')
    product.url = context['rev_url']
    product.ssid = data.xpath('//div[@class="site-content"]/article[contains(@class,"status-publish")]/@id').string()
    product.category = context['cat']
    
    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid
    review.date = context['datetime']

    author = context['author']
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//div[@id="review_score"]//h3/text()').string()
    if grade_overall:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    summary = data.xpath('//div[@id="review_summary_text"]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    excerpt = data.xpath('//div[@class="entry-content"]//p//text()').string(multiple=True)
    if excerpt:
        excerpt = excerpt.split("We behandelen je gegevens met respect en sturen geen spam. Lees meer over")[0]
        if summary:
            excerpt = excerpt.replace(summary, '').strip()
        
        review.add_property(type='excerpt', value=excerpt)
        product.reviews.append(review)
        session.emit(product)