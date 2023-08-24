from agent import *
from models.products import *


def run(context, session):
    session.queue(Request("https://musicplayers.com/category/reviews/"), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='bk-blog-content clearfix']//h4/a")
    for rev in revs:
        title = rev.xpath(".//text()").string().encode('ascii', errors='ignore').strip()
        url = rev.xpath("@href").string()
        session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url  = data.xpath('//link[@rel="next"]/@href').string()
    if next_url :
        session.queue(Request(next_url), process_revlist, dict())


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split("Album Review:")[-1].split("Album Review -")[-1].split("ALBUM REVIEW:")[-1].split("DVD Review:")[-1].split(":")[0].split(" - ")[0].strip()
    product.url = context['url']
    product.ssid = context['url'].split("/")[-2].replace('%ef%bb%bf', '')

    categories = data.xpath('//div[@class="breadcrumbs"]//span[@itemprop="title" and not(text()="Home" or text()="Reviews")]/text()').strings()
    if categories:
        categories = [cat.replace('Reviews:', '').replace('Review:', '').replace('Reviews', '').replace('Review', '').strip() for cat in categories]
        product.category = '|'.join(categories)
    else:
        product.category = data.xpath('//meta[@property="article:section"]/@content').string().replace('Reviews:', '').replace('Review:', '').replace('Reviews', '').replace('Review', '').strip()

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = context['title']

    date = data.xpath('//meta[@itemprop="datePublished"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@rel="author"]').first()
    if author:
        name = author.xpath(".//text()").string()
        url = author.xpath("@href").string()
        ssid = url.split("/")[-2].replace('%ef%bb%bf', '')
        review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

    grades = data.xpath("//tbody/tr/following-sibling::tr")
    for grade in grades:
        name = grade.xpath(".//strong/text()").string()
        if not name:
            name = grade.xpath(".//span/text()").string()
        value = grade.xpath(".//img/@src").string()

        if name and value and name != 'Overall Rating:':
            value = value.split('/')[-1].split('.')[0].replace("finalstar-", "").replace("_stars", "").replace("_", "")
            try:
                if float(value) > 10.0:
                    value = float(value) / 10
                review.grades.append(Grade(name=name.replace(':', ''), value=float(value), best=4.0))
            except ValueError:
                pass

    grade_overall = data.xpath('//tr[contains(., "Overall Rating")]//text()|//span[contains(., "OVERALL RATING")]//text()|//tr[contains(., "Overall")]//text()').string(multiple=True)
    if grade_overall:
        grade_overall = grade_overall.lower().replace('overall', '').replace('rating', '').split('stars')[0].split('=')[-1].split(',')[0].replace(':', '').strip()
        try:
            grade_overall = float(grade_overall)
        except ValueError:
            grade_overall = None
    if not grade_overall:
        grade_overall = data.xpath('//tr[contains(., "Overall Rating")]//img/@src|//span[contains(., "OVERALL RATING")]//text()|//tr[contains(., "Overall")]//img/@src').string()
        if grade_overall:
            grade_overall = grade_overall.split('/')[-1].split('.')[0].replace("finalstar-", "").replace("_stars", "").replace("_", "")
            try:
                grade_overall = float(grade_overall)
            except ValueError:
                grade_overall = None
    if grade_overall:
        review.grades.append(Grade(type='overall', value=grade_overall, best=4.0))

    conclusion = data.xpath('//div[@class="article-content clearfix"]/p[contains(., "The Verdict:")]/following-sibling::p[not(contains(., "www.")) and not(contains(., "Overall Rating")) and not(contains(., "Contact Information"))]/text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    if conclusion:
        excerpt = data.xpath('//div[@class="article-content clearfix"]/p[contains(., "The Verdict:")]/preceding-sibling::p[not(contains(., "www.")) and not(contains(., "Overall Rating")) and not(contains(., "Contact Information"))]/text()').string(multiple=True)
    else:
        excerpt = data.xpath('//div[@class="entrytext"]/p[not(contains(., "www.")) and not(contains(., "Overall Rating")) and not(contains(., "Contact Information"))]/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-content clearfix"]/p[not(contains(., "www.")) and not(contains(., "Overall Rating")) and not(contains(., "Contact Information"))]/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@class="article-content clearfix"]/p[not(contains(., "www.")) and not(contains(., "Overall Rating")) and not(contains(., "Contact Information"))]/span/text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[@itemprop="articleBody"]/h3[contains(text(), "Contact Information")]/preceding-sibling::text()').string(multiple=True)
    if not excerpt:
            excerpt = data.xpath('//div[@itemprop="articleBody"]/p[not(contains(., "www.")) and not(contains(., "Overall Rating")) and not(contains(., "Contact Information"))]/text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
