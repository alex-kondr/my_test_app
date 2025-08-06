from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.filmrecensiepagina.nl/films-filmoverzicht.htm'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath('//p[@align="center"]//b//a')
    for rev in revs:
        name = rev.xpath('.//text()').string(multiple=True)
        url ='https://filmrecensiepagina.nl/' + rev.xpath('@href').string().split('/')[-1]

        if name and url:
            session.queue(Request(url), process_review, dict(name=name, url=url))

# no next page


def process_review(data, context, session):
    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.htm', '')
    product.category = 'Films'

    review = Review()
    review.type = 'pro'
    review.title = product.name
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//p[@align="left"]//text()[normalize-space(.)]').string()
    if date:
        date = re.search(r'\( ?\d+\)', date)
        if date:
            review.date = date.group().strip('( )')

    author = data.xpath('//p[@align="left"]//text()[normalize-space(.)]').string()
    if author:
        author = re.split(r'\(\d+\)', author.split(', van ')[-1].split(u',\xa0van ')[-1].split(',  van ')[-1], maxsplit=1)[0].replace('regisseur(s)', '').replace('regisseur', '').strip()
        if author:
            review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//p[not(@align)]//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[@align="left"]//text()').string(multiple=True)

    if excerpt:
        excerpt = re.split(r'\(\d+\)', excerpt)[-1]
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
