from agent import *
from models.products import *
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("https://spielekritik.blogspot.com/search?updated-max=2025-01-01T07:00:00%2B01:00&max-results=7", use="curl", max_age=0), process_revlist, dict())


def process_token(data, context, session):
    session.do(Request(context['url'], use='curl', max_age=0), context['next_func'], dict(context))


def process_revlist(data, context, session):
    captcha = data.xpath('//div[@class="g-recaptcha"]')
    if captcha:
        token = data.xpath('//input[@name="q"]/@value').string()
        session.do(Request('https://spielekritik.blogspot.com/?token=' + token, use='curl', max_age=0), process_token, dict(url=data.response_url, next_func=process_revlist))
        return

    revs = data.xpath('//h3[contains(@class, "title")]/a')
    for rev in revs:
        title = rev.xpath("text()").string(multiple=True)
        url = rev.xpath("@href").string(multiple=True)
        session.queue(Request(url, use="curl", max_age=0), process_review, dict(title=title, url=url))

    next_url = data.xpath("//span[@id='blog-pager-older-link']/a//@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl", max_age=0), process_revlist, dict())


def process_review(data, context, session):
    captcha = data.xpath('//div[@class="g-recaptcha"]')
    if captcha:
        token = data.xpath('//input[@name="q"]/@value').string()
        session.do(Request('https://spielekritik.blogspot.com/?token=' + token, use='curl', max_age=0), process_token, dict(context, url=data.response_url, next_func=process_review))
        return

    product = Product()
    product.url = context['url']
    product.ssid = context['url'].split('/')[-1].replace('.html', '')
    product.category = 'Spiele'

    product.name = context['title'].split('.', 1)[-1].split("Rezension:")[-1].strip(' .')
    if len(product.name) < 2:
        product.name = context['title']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//h2[contains(@class, "date")]/span/text()').string()
    if date:
        review.date = date.split(', ')[-1].strip()

    author = data.xpath('//span[contains(@class, "author")]/span/text()').string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[contains(@class, "entry-content")]//text()').string(multiple=True)
    if excerpt:
        excerpt = re.split(r"Das \d+\. Montagsspielen", excerpt)[0].strip()

        if 'Fazit:' in excerpt:
            excerpt, conclusion = excerpt.split('Fazit:', 1)
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt.strip())

        product.reviews.append(review)

        session.emit(product)
