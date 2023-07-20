from agent import *
from models.products import *


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.amateurphotographer.co.uk/"), process_frontpage, dict())
    
    
def process_frontpage(data, context, session):
    cats = data.xpath('//li[contains(@class, "menu-item")][a[text()="Reviews"]]//li/a')
    for cat in cats:
        name = cat.xpath('text()').string()
        url = cat.xpath('@href').string()
        session.queue(Request(url), process_revlist, dict(cat=name))
        

def process_revlist(data, context, session):
    revs = data.xpath("//ul[@class='posts-list']/li")
    for rev in revs:
        name = rev.xpath(".//h2/text()").string()
        url = rev.xpath(".//a/@href").string()
        ssid = rev.xpath("@class").string()[5:12].replace(" r", '')
        session.queue(Request(url), process_review, dict(context, name=name, url=url, ssid=ssid))

    next_page = data.xpath('//link[@rel="next"]/@href').string()
    if next_page:
        session.queue(Request(next_page), process_revlist, dict(context))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath("//h3[@class='productname']/text()").string() or context["name"].split('|')[0].split(" review")[0].split(" Test")[0].strip()
    product.ssid = context["ssid"]
    product.url = context["url"]
    product.category = context["cat"]
    product.manufacturer = data.xpath('//li[h3[contains(text(), "Manufacturer")]]//a/text()').string()

    review = Review()
    review.type = "pro"
    review.ssid = product.ssid
    review.url = context["url"]
    review.date = data.xpath('//body/p[@class="date"]/text()').string()

    grades = data.xpath('//div[@class="desktop-only"]//ul[@class="ratings"]/li')
    print(grades)
    for grade in grades:
        name = grade.xpath("h3/text()").string()
        value = grade.xpath("p/text()").string()
        if value:
            value = float(value.split('out')[0].replace(':', '').replace('-', '.').strip())
            if 'overall' in name.lower():
                review.grades.append(Grade(type='overall', value=value, best=5.0))
            else:
                review.grades.append(Grade(name=name, value=value, best=5.0))

    pros = data.xpath('//div[@class="desktop-only"]//p[@class="pros"]/text()').strings()
    for pro in pros:
        pro = pro.replace("+ ", '').strip()
        if pro:
            review.add_property(type="pros", value=pro)

    cons = data.xpath('//div[@class="desktop-only"]//p[@class="cons"]/text()').strings()
    for con in cons:
        con = con.replace("- ", '').strip()
        if con:
            review.add_property(type="cons", value=con)

    excerpt = data.xpath('//div[@class="editable-content"]//text()').string(multiple=True)
    # next_page = data.xpath("//p[@class='post-nav-links']/span/following-sibling::a/@href").string()
    # if next_page:
    #     if excerpt:
    #         review.add_property(type="summary", value=excerpt)
    #     session.do(Request(next_page), process_lastpage, dict(product=product, review=review, url=next_page))
    #     return

    summary = data.xpath('//div[@class="post-excerpt-content"]/text()').string()
    if summary:
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//li[h3[contains(text(), "Verdict")]]/p/text()').string()
    if conclusion:
        review.add_property(type="conclusion", value=conclusion)

    # if excerpt:
    #     if conclusion:
    #         excerpt = excerpt.replace(conclusion.strip(), '').strip()
    #     review.add_property(type="excerpt", value=excerpt)
    #     product.reviews.append(review)
    #     session.emit(product)