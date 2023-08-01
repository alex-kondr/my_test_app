from agent import *
from models.products import *
import re


def run(context, session):
    session.queue(Request('https://www.consolewars.de/reviews/'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='reviewitembox column widthconstrained']")
    for rev in revs:
        name = rev.xpath(".//div[@class='content growfull']/h2/text()").string()
        url = rev.xpath(".//a[@shape='rect']/@href").string()
        session.queue(Request(url), process_review, dict(context, name=name, url=url))


def process_review(data, context, session):
    product = Product()

    category = data.xpath('//h3[@id="games_genre"]/span/text()').string()
    platform = data.xpath('//div[@id="review_system"]/span/text()').string()
    if category and platform:
        category = platform + '|' + category
    if category:
        product.category = 'Games|' + category
    else:
        product.category = 'Games'

    product.name = context['name']
    product.url = context['url']
    product.ssid = context['url'].split("/")[-3]

    review = Review()
    review.type = 'pro'
    review.url = product.url
    review.ssid = product.ssid
    review.title = data.xpath('//h1[@class="games_gametitle"]/span/text()').string(multiple=True)

    date = data.xpath("//time[@itemprop='datePublished']/@datetime").string()
    if date:
        review.date = date.split(" ")[0]

    author_name = data.xpath("//div[@class='wrapper topmostwrapper']/a/span/text()").string()
    author_url = data.xpath("//div[@class='wrapper topmostwrapper']/a/@href").string()
    if author_name and author_url:
        review.authors.append(Person(name=author_name, ssid=author_url, profile_url=author_url))

    grade_overall = data.xpath("//span[@class='review_endpoints']/text()").string()
    if grade_overall:
        best = grade_overall.split('/')[1]
        grade = grade_overall.split('/')[0]
        review.grades.append(Grade(type='overall', value=float(grade), best=float(best)))

    grade = data.xpath('//span[@id="user_endpointsavg"]/text()').string()
    if grade:
        review.grades.append(Grade(name='Userwertung', value=float(grade), best=10.0))

    grades_values_script = data.xpath("//script[contains(., '.setRate')]/text()").string()
    grades_values_arr = re.findall(r'cw_review\.setRate\("rate[0-9]", [0-9]\);', grades_values_script)
    grades_values = []
    number_rates = []
    for gr in grades_values_arr:
        grades_values.append(int(re.findall(r'[0-9]', gr)[1]))
        number_rates.append(int(re.findall(r'[0-9]', gr)[0]))

    grades_names = data.xpath('//div[@class="row facenter"]')
    for grade in range(0, len(grades_names) - 1):
        name = data.xpath('//div[@class="row facenter"][.//div[@class="inner bar_rate' + str(number_rates[grade]) + '"]]//div[@class="desc"]//text()').string()
        if name:
            review.grades.append(Grade(name=name.split(' (')[0], value=float(grades_values[grade]), best=5.0))

    pros = data.xpath('//div[@id="review_pro"]/div[@class="contenteditdiv"]//text()[normalize-space(.)]').strings()
    for pro in pros:
        pro = pro.replace('+', '').replace(' -', '').replace('- ', '').replace('...', '').replace('…', '').strip()
        review.add_property(type='pros', value=pro)

    cons = data.xpath('//div[@id="review_pro"]/div[@class="contenteditdiv"]//text()[normalize-space(.)]').strings()
    for con in cons:
        con = con.replace('+', '').replace(' -', '').replace('- ', '').replace('...', '').replace('…', '').strip()
        review.add_property(type='cons', value=con)

    summary = data.xpath('//h2[@id="review_headline"]/span[@itemprop="author"]/text()').string()
    if summary:
        review.properties.append(ReviewProperty(type='summary', value=summary))

    conclusion = data.xpath('//div[@id="review_commentary"]/div[@class="contenteditdiv"]/span/text()').string(multiple=True)
    if conclusion:
        review.properties.append(ReviewProperty(type='conclusion', value=conclusion))

    excerpt = data.xpath('//div[@id="review_content"]/div[@class="contenteditdiv"]/h3/span/text()|//div[@id="review_content"]/div[@class="contenteditdiv"]/span/text()').string(multiple=True)
    if excerpt:
        review.properties.append(ReviewProperty(type='excerpt', value=excerpt))

        product.reviews.append(review)

        session.emit(product)
