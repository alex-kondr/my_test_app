from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
   session.queue(Request('https://www.testfazit.de/?s=im+test', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data: Response, context: dict[str, str], session: Session):
    for prod in data.xpath("//a[@rel='bookmark']"):
        url = prod.xpath("@href").string()
        title = prod.xpath("text()").string(multiple=True)

        if url and title:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(url=url, title=title))

    next_url = data.xpath('//a[contains(@class, "next")]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_frontpage, dict())


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['title'].replace('im Test', '').replace(' Testbericht', '').replace(' TestFazit.de', '').replace(' Test', '').strip()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-2].replace('-test', '')
    product.category = data.xpath("(//a[@itemprop='item'])[last()]//text()").string().replace(' Test', '')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid

    conclusion = data.xpath("//h2[contains(., 'Fazit')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        conclusion = conclusion.replace(u'Ã‚Âœ ', ' – ')
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "Fazit")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath("//div[contains(@class,'entry-content')]//p//text()").string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
