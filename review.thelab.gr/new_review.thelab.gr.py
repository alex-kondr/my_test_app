from agent import *
from models.products import *


def strip_namespace(data):
    tmp = data.content_file + ".tmp"
    out = file(tmp, "w")
    for line in file(data.content_file):
        line = line.replace('<ns0', '<')
        line = line.replace('ns0:', '')
        line = line.replace(' xmlns', ' abcde=')
        out.write(line + "\n")
    out.close()
    os.rename(tmp, data.content_file)


def run(context: dict[str, str], session: Session):
    session.queue(Request('https://www.thelab.gr/reviews/', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    revs = data.xpath("//*[@class='ipsSpacer_both' or @class='ipsType_break']//a")
    for rev in revs:
        title = rev.xpath(".//text()").string(multiple=True)
        url = rev.xpath("@href").string()

        if '/reviews/' in url:
            session.queue(Request(url, force_charset='utf-8'), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//a[@rel="next"]/@href').string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    strip_namespace(data)

    product = Product()
    product.name = context['title'].split(' Review')[0].split(' review: ')[0].replace('[REVIEW] ', '').replace(' Cooler_Review', '').replace('Review ', '').replace(' review', '').strip(' ,')
    product.url = context['url']
    product.ssid = product.url.split('/')[-2].replace('.html', '')
    product.category = 'Τεχνολογία'

    category = data.xpath('(//ul[@data-role="breadcrumbList"]/li/a)[last()]//text()').string(multiple=True)
    if category:
        category = category.replace(' Reviews', '')
        if 'reviews' not in category.lower():
            product.category = category

    manufacturer = data.xpath('//div[contains(@class, "manufacturer")]/img/@alt').string()
    if manufacturer:
        product.manufacturer = manufacturer.title()

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.ssid = product.ssid
    review.url = context['url']

    date = data.xpath("//abbr[@class='published']//text()").string()
    if not date:
        date = data.xpath('//meta[@property="og:updated_time"]/@content').string()

    if date:
        review.date = date.split('T')[0]

    authors = data.xpath("//div[@class='postMeta--author-author metaFont']/a")
    for author in authors:
        author_name = author.xpath(".//text()").string(multiple=True)
        author_url = author.xpath("@href").string()
        author_ssid = author_url.split('/')[-2].split('-')[0]
        review.authors.append(Person(name=author_name, ssid=author_ssid, profile_url=author_url))

    grades_val = []
    grades = data.xpath('//div[@class="review-points"]/table//tr[td[not(@style)]]')
    for grade in grades:
        grade_name = grade.xpath('td[1]/text()').string()
        grade_val = grade.xpath('td[2]/text()').string()
        if grade_name and grade_val and grade_val[0].isdigit() and float(grade_val) > 0:
            grade_name = grade_name.strip(' +-*.:;•,–')
            grades_val.append(float(grade_val))
            review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    if grades_val:
        grade_overall = round(sum(grades_val) / len(grades_val), 1)
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = data.xpath('(//p[.//img[contains(@data-fileid, "uppng")]]/following-sibling::ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True)
        if pro:
            pro = pro.strip(' +-*.:;•,–')
            if len(pro) > 1:
                review.add_property(type='pros', value=pro)

    cons = data.xpath('(//p[.//img[contains(@data-fileid, "downpng")]]/following-sibling::ul)[1]/li')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True)
        if con:
            con = con.strip(' +-*.:;•,–')
            if len(con) > 1:
                review.add_property(type='cons', value=con)

    conclusion = data.xpath('//p[normalize-space(.//span/text())="Συμπεράσματα" or normalize-space(.//span/text())="Εν κατακλείδι:" or normalize-space(.//span/text())="Επίλογος"]/following-sibling::p[not(preceding-sibling::p//img[contains(@data-fileid, "uppng") or contains(@data-fileid, "downpng")] or contains(., "πλεονεκτήματα και μειονεκτήματα"))][not(preceding-sibling::p[contains(., "Βαθμολογία:")] or contains(., "Βαθμολογία:"))]//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//p[normalize-space(.//span/text())="Συμπεράσματα" or normalize-space(.//span/text())="Εν κατακλείδι:" or normalize-space(.//span/text())="Επίλογος"]/preceding-sibling::p//text()').string(multiple=True)
    if not excerpt:
        excerpt = data.xpath('//div[section]/p[not(preceding::p//img[contains(@data-fileid, "uppng") or contains(@data-fileid, "downpng")] or contains(., "πλεονεκτήματα και μειονεκτήματα"))][not(preceding-sibling::p[contains(., "Βαθμολογία:")] or contains(., "Βαθμολογία:"))]//text()').string(multiple=True)

    if excerpt:
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
