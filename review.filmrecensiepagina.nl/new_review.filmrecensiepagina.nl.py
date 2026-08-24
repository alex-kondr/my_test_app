from agent import *
from models.products import *
import re


def cleaned_text(text):
    return text.replace(u'Ã§', u'ç').replace(u'Ã«', u'ë').replace(u'Ã©Ã©n', u'éé').replace(u'Ã¯', u'ï').replace(u'Ã¼', u'ü').replace(u'Ã¤', u'ä').replace(u'Ã¨', u'è').replace(u'Ã©', u'é').strip()


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.filmrecensiepagina.nl/films-filmoverzicht.htm', use='curl'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//p[@align="center"]/big/font/big/a[not(contains(@href, "updates1"))]')
    for rev in revs:
        name = rev.xpath('text()').string()
        url = rev.xpath('@href').string()

        if name and url:
            session.queue(Request(url, use='curl'), process_review, dict(name=name, url=url))

    # no next page


def process_review(data: Response, context: dict[str, str], session: Session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '').replace('.htm', '')
    product.category = 'Films'

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    date_author = data.xpath('//blockquote/p//text()[normalize-space()]').string(multiple=True)
    if not date_author:
        date_author = data.xpath('//p[.//img[contains(@src, "pinkpan.gif")]]/following-sibling::p//text()[normalize-space(.)]').string(multiple=True)

    if date_author:
        date_author = re.search(r'(van.*?)\(( ?\d{4}) ?\)', date_author, re.DOTALL)
        if date_author:
            review.date = date_author.group(2).strip()

            author = cleaned_text(date_author.group(1).split('van ')[-1].split('(')[0].split('regisseurs')[-1].split('regisseur')[-1].split(' Zomer')[0])
            if author:
                review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//blockquote/p//text()[normalize-space()]').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[.//img[contains(@src, "pinkpan.gif")]]/following-sibling::p[following-sibling::h3[.//img[contains(@src, "pinkpan.gif")]]]//text()[normalize-space()]').string(multiple=True)

    if excerpt:
        excerpt = cleaned_text(re.split(r'\(\s*\d+\)', excerpt)[-1]).strip(' \n.')
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)

            session.emit(product)
