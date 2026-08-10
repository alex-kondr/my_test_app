from agent import *
from models.products import *


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=7000)]
    session.queue(Request('https://www.iceinspace.com.au/reviews.html', use='curl', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    cats = data.xpath('//h3')
    for cat in cats:
        cat_name = cat.xpath('text()').string()

        revs = cat.xpath('following-sibling::table[1]//tr/td/a')
        for rev in revs:
            name = rev.xpath('text()').string()
            url = rev.xpath('@href').string()
            session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(cat=cat_name, name=name, url=url))


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-2]

    product.category = context['cat'].replace('Other Reviews', '').replace(' Reviews', '').strip()
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.type = 'pro'
    review.title = context['name']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//div[@class="newsArticleSub"]/text()[contains(., "Submitted:")]').string()
    if date:
        review.date = date.replace('Submitted:', '').split(' by ')[0].split(', ')[-1].strip()

    author = data.xpath('(//p[contains(., "Review by")]/a)[1]/text()').string()
    author_url = data.xpath('(//p[contains(., "Review by")]/a)[1]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('=')[-1]
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    conclusion = data.xpath('(//h3[contains(., "Conclusion")]|//h4[contains(., "Summary.  Good and")])/following-sibling::p[not(contains(., "Review by"))]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[contains(., "Bottom line –")]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace('Bottom line –', '').strip().capitalize()
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//td/p[not(contains(., "Bottom line –") or contains(., "Review by") or preceding::p[contains(., "Bottom line –")] or preceding::h3[contains(., "Conclusion")] or preceding::h4[contains(., "Summary.  Good and")])]//text()').string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
