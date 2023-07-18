from agent import *
from models.products import *
import datetime
import simplejson


def process_frontpage(data, context, session):
    now = datetime.datetime.now()
    url = 'https://apps.wix.com/_api/communities-blog-node-api/_api/posts?categoryIds=5d7a1d780ca303001729188c&featuredOnly=false&cursor=' + str(now).split(' ')[0]  + 'T07%3A10%3A30.325Z&size=24'
    options = "-H 'authorization: ZWCX7QfEnu5gbTf68tYX6qj0qUNZm8AHtfsoV3CDKw4.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIwLTA3LTE3VDEyOjExOjU4LjQwOVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiJmMDllNjIwZi1kMWI4LTQ0MWYtOGEwMS03M2MyYjliNTk0YWYiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ'"
    session.queue(Request(url, use='curl', options=options, max_age=0), process_revlist, dict(context, last_date=str(now).split(' ')[0]))
   

def process_revlist(data, context, session):
    data = simplejson.loads(data.content)
    date = ''
    for rev in data:
        ssid = rev['id']
        title = rev['seoSlug']
        date = rev['createdDate'].split('T')[0]
        url = 'https://www.thegnet.org/post/' + title
        session.queue(Request(url, use='curl'), process_product, dict(date=date, ssid=ssid, url=url))
   
    if date and date != context['last_date']:
        url = 'https://apps.wix.com/_api/communities-blog-node-api/_api/posts?categoryIds=5d7a1d780ca303001729188c&featuredOnly=false&cursor=' + date + 'T07%3A10%3A30.325Z&size=24'
        options = "-H 'authorization: ZWCX7QfEnu5gbTf68tYX6qj0qUNZm8AHtfsoV3CDKw4.eyJpbnN0YW5jZUlkIjoiNmRmZjQ2OTgtZmJiZS00MjE5LWJlYWUtMGU5ZGQ1ZjQ5MTc4IiwiYXBwRGVmSWQiOiIxNGJjZGVkNy0wMDY2LTdjMzUtMTRkNy00NjZjYjNmMDkxMDMiLCJtZXRhU2l0ZUlkIjoiZDM5ZTJhMTMtYzE3ZC00NzdmLThjNDAtYjc5YTQ4ZjYyMWY1Iiwic2lnbkRhdGUiOiIyMDIwLTA3LTE3VDEyOjExOjU4LjQwOVoiLCJkZW1vTW9kZSI6ZmFsc2UsIm9yaWdpbkluc3RhbmNlSWQiOiJiNDUyYTIyMC0wOTgxLTRlMmUtYTY4Ny05ZGEzY2JjZmExOWYiLCJhaWQiOiJmMDllNjIwZi1kMWI4LTQ0MWYtOGEwMS03M2MyYjliNTk0YWYiLCJiaVRva2VuIjoiYmU2MTZjOGItM2FjMy0wNTY2LTMyZWUtYjkwNzlkMDJiMDhkIiwic2l0ZU93bmVySWQiOiIwNTJkMTgxZC0wNTIxLTQwODYtYTg2NC0xMWNkMTU5OGU2ZDIifQ'"
        session.queue(Request(url, use='curl', options=options, max_age=0), process_revlist, dict(last_date=date))


def process_product(data, context, session):
    title = data.xpath("//span[@class='blog-post-title-font blog-post-title-color']//text()").string()
    if not title:
        return 

    product = Product()
    product.name = title.split('The(G)net Review: ')[-1]
    product.category = data.xpath("//ul//li[1]//a[@data-hook='category-label-list__item']//text()").string()           
    product.url = context['url']
    product.ssid = context['ssid']

    review = Review()
    review.ssid = product.ssid
    review.url = product.url
    review.title = title
    review.type = 'pro'
    review.date = context['date']

    for img in data.xpath("//img"):
        image_src = img.xpath("@src").string()
        image_alt = img.xpath(".//parent::div//following-sibling::span//text()").string()
        if image_src and not('logo-g-gross.png' in image_src) and not('scn-logo.png' in image_src):
            if not image_alt:
                image_alt = product.name
            product.properties.append(ProductProperty(type=ProductPropertyType(name="image"), value = { 'src': image_src.replace('/thumb/', '/picture/'), 'alt': image_alt, 'type': 'screenshot'}))

    for con in data.xpath("//strong[contains(text(), 'Negativ')]//parent::p//following-sibling::p"):
        if con.xpath(".//strong"):
            break
        if con:
            con = con.xpath("text()").string()
            review.properties.append(ReviewProperty(type='cons', value=con))

    for pro in data.xpath("//strong[contains(text(), 'Positiv')]//parent::p//following-sibling::p"):
        if pro.xpath(".//strong"):
            break
        if pro:
            pro = pro.xpath("text()").string()
            review.properties.append(ReviewProperty(type='pros', value=pro))

    conclusion = data.xpath("//span[contains(text(), 'Fazit')]//parent::strong//parent::p//following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//span[contains(text(), 'Fazit')]//parent::strong//parent::h2//following-sibling::p//text()").string(multiple=True)
    if not conclusion:
        conclusion = data.xpath("//strong[contains(text(), 'Fazit')]//following-sibling::text()").string(multiple=True)
    if conclusion: 
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    summary = data.xpath("//p[@id='viewer-foo']//strong//text()").string(multiple=True)
    if not summary:
        summary = data.xpath("//p[@id='viewer-foo']//text()").string(multiple=True)
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath("//div[@data-hook='post-description']//p//text()").string(multiple=True)
    if excerpt and summary in excerpt:
        excerpt = excerpt.replace(summary, "")
    if excerpt and conclusion in excerpt:
        excerpt = excerpt.replace(conclusion, "")
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

    if conclusion or summary or excerpt:
        product.reviews.append(review)
        session.emit(product)


def run(context, session): 
    session.queue(Request('https://www.thegnet.org/reviews', use='curl'), process_frontpage, {})
