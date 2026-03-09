from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://gear-vault.com/guitars/", use='curl',force_charset='utf-8'), process_revlist, dict(cat='Guitars'))
    session.queue(Request("https://gear-vault.com/amplifiers/", use='curl',force_charset='utf-8'), process_revlist, dict(cat='Amplifiers'))


def process_revlist(data, context, session):
    for rev in data.xpath('//h3[contains(@class, "title")]/a'):
        title = rev.xpath('text()').string()
        url = rev.xpath("@href").string()

        if 'review' in title.lower():
            session.queue(Request(url, use='curl', max_age=0,force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath("//a[@class='next page-numbers']//@href").string()
    if next_url:
        session.queue(Request(next_url, use='curl',force_charset='utf-8'), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].replace('Reviewing the ', '').replace(' [Review]', '').replace(" Review", '').replace(' review', '').strip()
    product.url = context['url']
    product.ssid = context['url'].split("/")[-2].replace('-review', '')
    product.category = context['cat']

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//div[contains(@class, "content")]/div/span[contains(@class, "author")]//text()').string(multiple=True)
    author_url = data.xpath('//div[contains(@class, "content")]/div/span[contains(@class, "author")]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-2]
        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))
    elif author:
        review.authors.append(Person(name=author, ssid=author_ssid))

    conclusion = data.xpath("//div[@class='entry-content clearfix']//p[contains(., 'Conclusion:') ]/strong//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[regexp:test(., "THE VERDICT", "i")]//text()[not(regexp:test(., "THE VERDICT", "i"))]').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "The Verdict")]/following-sibling::p[1]//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//h2[contains(., "THE END LINE")]/following-sibling::p//text()').string(multiple=True)
    if not conclusion:
        conclusion = data.xpath('//p[strong[contains(., "Conclusion")]]/following-sibling::p[not(contains(., "Written by "))]//text()').string(multiple=True)

    if conclusion:
        conclusion = conclusion.replace("Conclusion: ", "")
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//h2[contains(., "THE END LINE")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[strong[contains(., "Conclusion")]]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//p[regexp:test(., "THE VERDICT", "i")]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[contains(@class, "entry-content")]/p[not(contains(., "Written by "))]//text()').string(multiple=True)

    if excerpt:
        excerpt = excerpt.split("Conclusion:")[0].replace('REVIEW — ', '')
        if conclusion:
            excerpt = excerpt.replace(conclusion, '').split('Originally published on')[0]

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
