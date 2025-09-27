from agent import *
from models.products import *


TOKEN = 'EgQSz4j1GLCooMYGIi0iHFJx2cfDhwsnXQCLcF3qtVoEhOwcZ9sHz6rci_ef-37PmhYfY9GnBl4PJKYyAnJSWgFD'


def run(context, session):
    session.queue(Request("http://rezensionen-fuer-millionen.blogspot.com/2008/04/register.html?token=" + TOKEN), process_revlist, {})


def process_revlist(data, context, session):
    for rev in data.xpath("//div[contains(@class, 'entry-content')]/p//a"):
        name = rev.xpath("text()").string(multiple=True)
        url = rev.xpath("@href").string(multiple=True)
        if url and name:
            session.queue(Request(url + '?token=' + TOKEN), process_review, dict(name=name, url=url))


def process_review(data, context, session):
    captcha = data.xpath('//div[@class="g-recaptcha"]')
    if captcha:
        token = data.xpath('//input[@name="q"]/@value').string()
        session.do(Request(data.response_url + '?token=' + token, use='curl', max_age=0), process_review, dict(context))
        return

    product = Product()
    product.name = context['name']
    product.url = context['url']
    product.ssid = product.url.split('/')[-1].replace('.html', '')
    product.category = 'Spiele'

    review = Review()
    review.type = 'pro'
    review.title = data.xpath("//h3[@class='post-title entry-title']/a/text()").string()
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath("//h2[@class='date-header']/text()").string()
    if date:
        review.date = date.split(',')[-1].strip()

    author = data.xpath("//span[@class='post-author vcard']/span/text()").string()
    if author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath("//span[@class='post-labels']/a/text()").string()
    if grade_overall:
        grade_overall = len(grade_overall.strip().split()[0])
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=7, worst=1))

    excerpt = data.xpath("//div[contains(@class, 'entry-content')]//text()").string(multiple=True)
    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
