from agent import *
from models.products import *


def run(context, session):
    session.queue(Request('http://bgr.com/reviews/'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='flex-1 w-full lg:max-w-[930px]']//h2//a[@href and text()]")
    for rev in revs:
        title = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        if title and url:
            session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath("//div[@class='nav-links']//a[contains(@class,'next')]/@href").string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context, next_url=next_url))


def process_review(data, context, session):
    product = Product()
    product.name = context['title'].split(' review: ')[0]
    product.url = context['url']
    product.category = data.xpath("(//div[@class='bgr-breadcrumbs mb-[0.563rem] sm:mb-[0.813rem]']//span/span/a/text())[3]").string()
    product.ssid = product.url.split('/')[-2]

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.url = context['url']
    review.type = 'pro'

    date = data.xpath("//meta[@property='article:modified_time']/@content").string()
    if date:
        if 'T' in date:
            date = date.split('T')[0]
        review.date = date

    author_name = data.xpath("//div[@class='text-[16px] leading-[20px] tracking-[-0.1px] font-bold font-helvetica-neue co-authors-meta']//span/a/text()").string()
    author_url = data.xpath("//div[@class='text-[16px] leading-[20px] tracking-[-0.1px] font-bold font-helvetica-neue co-authors-meta']//span/a/@href").string()
    if author_name:
        if author_url:
            review.authors.append(Person(name=author_name, ssid=author_name, profile_url=author_url))
        else:
            review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath("//div[@class='hidden md:block']/div//span/text()").string()
    if not grade_overall:
        grade_overall = data.xpath("//div[@class='bgr-commerce-stars mb-5 bgr-commerce-stars-4']//text()").string()
    if grade_overall:
        grade_overall = grade_overall.split()[1]
    else:
        grade_overall = len(data.xpath("//div[@class='text-blue']//span[@class='bgr-rating bgr-clip-100 bgr-rating-solid']/text()"))
        grade_overall += 0.5 * len(data.xpath("//div[@class='text-blue']//span[@class='bgr-rating bgr-clip-50 bgr-rating-solid']/text()"))
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

    summary = data.xpath('//div[@class="bgr-commerce-description flex-auto hidden md:block text-sm"]/p//span//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    pros = data.xpath("//ul[@class='pros']//li")
    for pro in pros:
        pro = pro.xpath(".//text()").string(multiple=True)
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath("//ul[@class='cons']//li")
    for con in cons:
        con = con.xpath(".//text()").string(multiple=True)
        if con:
            review.add_property(type='cons', value=con)

    conclusion = data.xpath("//div[@class='entry-content no-dropcap']//h2[contains(.,'Conclusion') or contains(.,'conclusions') or contains(.,'verdict') or contains(.,'Verdict')]/following-sibling::p//text()").string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath("//div[@class='entry-content no-dropcap']//text()[not(contains(., 'Conclusion') or contains(., 'conclusion') or contains(., 'conclusions') or contains(., 'verdict') or contains(., 'Verdict'))]/ancestor::p//text()").string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)
        session.emit(product)
