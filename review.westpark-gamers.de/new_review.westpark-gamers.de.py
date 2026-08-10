from agent import *
from models.products import *
import time
import random


def run(context: dict[str, str], session: Session):
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request("https://www.westpark-gamers.de/rangliste/", force_charset='utf-8'), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    revs = data.xpath('//table/tbody/tr/td/a')
    for rev in revs:
        name = rev.xpath("text()").string()
        url = rev.xpath("@href").string()
        session.queue(Request(url, force_charset='utf-8'), process_product, dict(name=name, url=url))

    # loaded all revs


def process_product(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    product = Product()
    product.name = context["name"]
    product.url = context["url"]
    product.ssid = product.url.split('=')[-1]
    product.category = "Board Games"
    product.manufacturer = data.xpath('//tr[contains(th, "Verlag")]/td/text()').string()

    review = Review()
    review.type = "pro"

    grade_overall = data.xpath('//td[contains(@class, "avg-rating")]/text()').string()
    if grade_overall and float(grade_overall) > 0:
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    grades = data.xpath('//tr[th[contains(., "Noten")]]/td/text()').string()
    if grades:
        grades = grades.split(', ')
        for grade in grades:
            grade_name, grade_val = grade.split(': ')
            if grade_name and grade_val[0].isdigit() and float(grade_val) > 0:
                review.grades.append(Grade(name=grade_name, value=float(grade_val), best=10.0))

    revs_url = data.xpath('//a[contains(., "review")]/@href').strings()
    for url in revs_url:
        review.url = url
        session.do(Request(url, force_charset='utf-8'), process_review, dict(product=product, review=review))


def process_review(data: Response, context: dict[str, str], session: Session):
    time.sleep(random.uniform(1, 3))

    review = context['review']

    review.title = data.xpath('//h1[contains(@class, "title")]/text()').string()

    review.ssid = review.url.split('/')[-1].split(".")[0].split("bericht")[-1].split('?p=')[-1]
    if not review.ssid:
        review.ssid = review.url.split('/')[-2]

    date = data.xpath('//time[contains(@class, "published")]/@datetime').string()
    if date:
        review.date = date.split('T')[0]

    author_url = data.xpath('//span[contains(@class, "author")]/a[not(contains(., "Webmaster"))]/@href').string()
    author = data.xpath("//p[regexp:test(text(), '^rezensiert von ', 'i')]/text()").string()
    if not author:
        author = data.xpath('//span[contains(@class, "author")]/a[not(contains(., "Webmaster"))]/text()').string()
    if not author:
        author =data.xpath("//h4[regexp:test(text(), '^reviewed by ', 'i')]/text()").string()
    if not author:
        author = data.xpath("//p[regexp:test(., '^reviewed by ', 'i')]//text()").string()
    if not author:
        author = data.xpath('//p[contains(b, "Author")]/text()').string()
    if not author:
        author = data.xpath('//p[contains(b, "Autor")]/text()').string()
    if not author:
        author = data.xpath("//p[regexp:test(., '^Quick look by ', 'i')]//text()").string()
    if not author:
        author = data.xpath('//tr[contains(td/text(), "Autor")]/td[not(contains(., "Autor"))]/text()').string()

    if author:
        author = author.split("rezensiert von ")[-1].split('reviewed by ')[-1].split('Quick look by ')[-1].strip(' :')

        if ', ' in author:
            authors = author.split(', ')
            for author in authors:
                review.authors.append(Person(name=author, ssid=author))
        elif author and author_url:
            author_ssid = author_url.split('/')[-2]
            review.authors.append(Person(name=author, ssid=author_ssid))
        elif author:
            review.authors.append(Person(name=author, ssid=author))

    excerpt = data.xpath('//div[@class="entry-content"]/p[not(contains(a, "Print this review") or regexp:test(., "^Publisher:|^Author:|^Tester:|^Game Tested:|Rating|Hersteller:|Autor:|Getestet:|Tester:"))]//text()[not(regexp:test(., "WPG-Wertung:|schreibt eine Rezension|rezensiert von |reviewed by |Quick look by |Wertung:|Gesamtnote"))]').string(multiple=True)
    if excerpt:
        if 'Fazit: ' in excerpt:
            excerpt, conclusion = excerpt.split('Fazit: ')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type="excerpt", value=excerpt.strip())

        product = context['product']
        product.reviews.append(review)

        session.emit(product)
