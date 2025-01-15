from agent import *
from models.products import *


def process_frontpage(data, context, session):
    for category in data.xpath("//h2/following::div[@class='sh-ratio-container']"):
        url = category.xpath("a/@href").string()
        name = category.xpath("h4/text()").string()
        if url and name:
            session.queue(Request(url, use='curl'), process_category, dict(category=name, cat_url=url, page=1))


def process_category(data, context, session):
    prods = data.xpath("//div[@class='post-content-container']")
    for prod in prods:
        title = prod.xpath("./h2/text()").string()
        url =  prod.xpath("./a/@href").string()
        if title and url and 'review' in url:
            session.queue(Request(url, use='curl'), process_product, dict(context, url=url, title=title))

    prods = data.xpath("//div[@class='wpb_wrapper']//p/a")
    for prod in prods:
        title = prod.xpath(".//text()").string()
        url = prod.xpath("@href").string()
        if title and url and 'review' in url:
            session.queue(Request(url, use='curl'), process_product, dict(context, url=url, title=title))

    if not data.xpath("//div[@class='sh-404-container']/div[@class='sh-404-description'][contains(., 'OOPS!')]"):
        context['page'] += 1
        url = context['cat_url'] + "page/" + str(context['page']) + "/" 
        session.queue(Request(url, use='curl'), process_category, context)


def process_product(data, context, session):
    product = Product()
    product.url = context["url"]
    product.name = context["title"].split("Review")[0].split("Product")[0]
    product.category = context["category"]
    product.ssid = context['url'].split("/")[-2]
    
    review = Review()
    review.url = context["url"]
    review.ssid = product.ssid
    review.type = "pro"
    review.title = context["title"]

    time = data.xpath("//meta[@property='article:published_time']/@content").string()
    if not time: # Only reviews and articles have time
        return
    review.date = time.split("T")[0]

    excerpt = data.xpath("//div[@class='post-content post-single-content']//text()").string(multiple=True).split("What We Liked")[0].split("SLR Lounge Approved")[-1]

    conclusion = data.xpath("//div[@class='post-content-review-verdict']/p/text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='post-content post-single-content']//span[contains(., 'Conclusion') or contains(., 'Thoughts') or contains(., 'Verdict')]/parent::*/following-sibling::*//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//div[@class='post-content post-single-content']//h2[contains(., 'Conclusion') or contains(., 'Thoughts') or contains(., 'Verdict')]/following-sibling::*//text()").string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(name="conclusion", type="conclusion", value=conclusion))
        excerpt = excerpt.split(conclusion)[0]

    review.properties.append(ReviewProperty(name="excerpt", type="excerpt", value=excerpt))

    author = data.xpath("//span[@class='post-auhor-date']/span/a[@class='post-author']").first()
    authorurl = author.xpath("@href").string()
    review.authors.append(Person(name=author.xpath("text()").string(), ssid=authorurl.split("/")[-2], profile_url=authorurl))

    pros = data.xpath("//div[@class='post-content post-single-content']//span[contains(., 'What We Liked')]/following::ul[1]/li[@class='li3']//text()")
    if not pros:
        pros = data.xpath("//ul[@class='post-content-review-pros']/li/text()")
    for pro in pros:
        review.add_property(type="pros", value=pro.string())
    
    cons = data.xpath("//div[@class='post-content post-single-content']//span[contains(., 'What Could Be Better')]/following::ul[1]/li[@class='li3']//text()")
    if not cons:
        cons = data.xpath("//ul[@class='post-content-review-cons']/li/text()")
    for con in cons:
        review.add_property(type="cons", value=con.string())

    if data.xpath("//img[contains(@src, 'stars')]/@src"):
        for score in data.xpath("//img[contains(@src, 'stars')]/@src"):
            grade = score.string().split("/")[-1].rsplit(".", 1)[0].split("-", 1)[-1]
            name = grade.rsplit("-", 2)[0].replace("-", " ")
            value = grade.rsplit("-")[-2]
            if name and value and value.isdigit():
                value = float(value)
                if 'overall' in name:
                    review.grades.append(Grade(name=name, type='overall', value=value, best=5.0))
                else:
                    review.grades.append(Grade(name=name, value=value, best=5.0))
    elif data.xpath("//div[@class='post-content-review-progressbar-item']/div[@class='row']/div[not(contains(@class, 'right'))]"):
        for grade in data.xpath("//div[@class='post-content-review-progressbar-item']/div[@class='row']/div[not(contains(@class, 'right'))]"):
            name = grade.xpath("text()").string()
            value = grade.xpath("./following-sibling::div[1]/text()").string()
            if name and value:
                review.grades.append(Grade(name=name, value=float(value), best=10.0))
        overall = float(data.xpath("//div[@class='post-content-review-score']/h4/text()").string())
        review.grades.append(Grade(type='overall', value=overall, best=10.0))

    product.reviews.append(review)
    session.emit(product)


def run(context, session):
    session.queue(Request('https://www.slrlounge.com/camera/', use='curl'), process_frontpage, {})
