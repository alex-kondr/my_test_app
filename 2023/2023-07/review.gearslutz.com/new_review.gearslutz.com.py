from agent import *
from models.products import *
import simplejson
import re


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=5000)]
    session.queue(Request("http://www.gearslutz.com/board/reviews/", use="curl"), process_prodlist, dict())


def process_prodlist(data, context, session):
    cats = data.xpath("//div[@class='review-info']//a[not(@p)]")
    for cat in cats:
        url = cat.xpath("@href").string()
        name = cat.xpath("text()").string()
        ssid = cat.xpath("@id").string().split('_')[-1]
        session.queue(Request(url, use="curl"), process_product, dict(context, url=url.split('?')[0], name=name, ssid=ssid))

    next_url = data.xpath("//a[@rel='next']/@href").string()
    if next_url:
        session.queue(Request(next_url, use="curl"), process_prodlist, dict(context))


def process_product(data, context, session):
    product = context.get("product")
    if not product:
        product = Product()
        product.name = context["name"]
        product.url = context["url"]
        product.ssid = context["ssid"]
        product.category = "Audio"

        info = data.xpath("//script[@type='application/ld+json'][contains(text(), '\"aggregateRating\"')]/text()").string()
        if info:
            info = simplejson.loads(info)
            product.name = info["name"]
            product.sku = info["sku"]
            product.manufacturer = info["brand"]["name"]

            mpn = info.get("mpn")
            if mpn:
                product.properties.append(ProductProperty(type='id.manufacturer', value=mpn))

    revs = data.xpath(r"//div[regexp:test(@id, 'edit\d+', 'i')][not(descendant::strong[regexp:test(text(), 'click here', 'i')])]")
    for rev in revs:
        review = Review()
        review.type = "user"
        review.ssid = rev.xpath("div[@class='review-text']/@data-postid").string()
        review.date = rev.xpath(".//span[article and header]//text()").string(multiple=True)
        review.url = context["url"]

        grades = rev.xpath("div[@class='review-text']//img[@class='rating-stars-m']")
        for grade in grades:
            name = grade.xpath("preceding-sibling::*[1][self::span]/text()").string()
            value = int(grade.xpath("@alt").string().split(" out of 5")[0])
            review.grades.append(Grade(name=name, value=value, best=5))

        overall = rev.xpath("div[@class='review-text']//img[@class='rating-stars-l']/@alt").string()
        if overall:
            review.grades.append(Grade(type="overall", value=float(overall), best=5.0))

        author = rev.xpath(".//a[contains(@href, '/board/member')]").first()
        if author:
            name = author.xpath("text()").string()
            if name and not "deleted user" in name.lower():
                url = author.xpath("@href").string()
                ssid = url.split("u=")[-1]
                review.authors.append(Person(name=name, ssid=ssid, profile_url=url))

        info = rev.xpath(".//div[contains(@id, 'post_message_')]").first()
        excerpt = info.xpath("*[self::p or self::span]//*[b or br or text()]//text()").string(multiple=True)
        if excerpt:
            pros = info.xpath("*[self::p or self::span]//b[regexp:test(text(), 'pros', 'i')]/following-sibling::text()")
            for pro in pros:
                pro = pro.string()
                if not pro:
                    break
                pro = pro.replace('•', '').replace('*', '').strip()
                if pro.startswith(" -") or pro.startswith("-"):
                    pro = pro.split("-", 1)[-1]
                review.add_property(type="pros", value=pro)
                excerpt = excerpt.replace(pro, '')

            cons = info.xpath("*[self::p or self::span]//b[regexp:test(text(), 'cons', 'i')]/following-sibling::text()")
            for con in cons:
                con = con.string()
                if not con:
                    break
                con = con.replace('•', '').replace('*', '').strip()
                if con.startswith(" -") or con.startswith("-"):
                    con = con.split("-", 1)[-1]
                review.add_property(type="cons", value=con)
                excerpt = excerpt.replace(con, '')

            summary_info = info.xpath("*[self::p or self::span]//b[regexp:test(text(), 'introducing|introduction|intro', 'i')]/following-sibling::text()")
            conclusion_info = info.xpath("*[self::p or self::span]//b[regexp:test(text(), 'conclusion', 'i')]/following-sibling::text()")
            if conclusion_info or summary_info:
                review.type = "pro"
                summary = ""
                for s in summary_info:
                    s = s.string()
                    if not s:
                        break
                    summary += s.strip()
                    excerpt = excerpt.split(summary)[-1]

                if summary:
                    review.add_property(type="summary", value=summary)

                conclusion = ""
                for s in conclusion_info:
                    s = s.string()
                    if s:
                        conclusion += s.strip()
                        excerpt = excerpt.replace(conclusion, '')

                if conclusion:
                    if " Cons: " in conclusion:
                        conclusion = conclusion.split(" Cons: ")[0]
                    if " Pros: " in conclusion:
                        conclusion = conclusion.split(" Pros: ")[0]
                    review.add_property(type="conclusion", value=conclusion)

            excerpt = re.sub(r"pros\W+Cons\W+(https:\/\/.*)?", '', excerpt, flags=re.IGNORECASE)
            excerpt = excerpt.strip()
            if excerpt:
                review.add_property(type="excerpt", value=excerpt)

            if (review.type == "pro" and (summary or excerpt or conclusion)) or (review.type == "user" and excerpt):
                product.reviews.append(review)

    next_url = data.xpath("//a[@rel='next']/@href").string()
    if next_url:
        session.do(Request(next_url, use="curl"), process_product, dict(product=product, url=next_url.split('?')[0]))
    elif product.reviews:
        session.emit(product)
