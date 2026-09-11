from agent import *
from models.products import *


XCAT = ['Autres tests']


def run(context: dict[str, str], session: Session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request("https://www.xboxfront.de/tests.html"), process_revlist, dict())


def process_revlist(data: Response, context: dict[str, str], session: Session):
    revs = data.xpath('//div[@class="info"]')
    for rev in revs:
        title = rev.xpath('div/a/text()').string()
        url = rev.xpath('div/a/@href').string()
        platform = rev.xpath('.//td[contains(., "System:")]/following-sibling::td/text()').string() or ''
        genre = rev.xpath('.//td[contains(., "Genre:")]/following-sibling::td/text()').string() or ''
        manufacturer = rev.xpath('.//td[contains(., "Publisher:")]/following-sibling::td/text()').string()
        prod_url = rev.xpath('.//td[contains(., "Website:")]/following-sibling::td/a/@href').string()
        if prod_url:
            prod_url = prod_url.split('redir.php?')[-1]

        session.queue(Request(url), process_review, dict(context, title=title, url=url, cat=platform+'|'+genre, manufacturer=manufacturer, prod_url=prod_url))

    next_url = data.xpath('//li[@class="page-item"][last()]/a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data: Response, context: dict[str, str], session: Session):
    if not data.xpath('//div[@class="block" or @class="bigfont block"]//text()'):
        # An empty page, need to request to first page
        url = data.xpath('//a[@class="page-link"][contains(., "1")]/@href').string()
        session.do(Request(url), process_review, dict(context))
        return

    product = Product()
    product.name = context['title'].split('Test:', 1)[-1].split('Preview:')[-1].split('Hands On:')[-1]
    product.manufacturer = context.get('manufacturer')
    product.category = context['cat'].strip(' |')
    product.url = context.get('prod_url') or data.xpath('//a[img[contains(@title, "Packshot:")]]/@href').string() or context['url']
    product.ssid = context['url'].split('/')[-1].split('.html')[0].split('test-', 1)[-1]

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    author_date = data.xpath('//div[@id="teaser_body_content"][last()]/div/text()').string()
    if author_date:
        review.date = author_date.split(':')[0].strip()

        author = author_date.split(':')[-1].strip()
        if author.lower() != 'xboxfront':
            review.authors.append(Person(name=author, ssid=author))

    summary = data.xpath('//div[@class="bigfont"]/div[position()=1]/strong/text()').string(multiple=True)
    if summary:
        context['summary'] = summary.strip()

    conclusion = data.xpath('//div[contains(text(), "Fazit:")]/following-sibling::div[1]/text()[not(contains(., "Pro und Contra"))][not(preceding::div[contains(., "Pro und Contra")])]').string(multiple=True)
    if conclusion:
        context['conclusion'] = conclusion.strip()

    excerpt = data.xpath('//div[@class="block" or @class="bigfont block"]/text()').string(multiple=True)
    if excerpt and not conclusion:
        context['excerpt'] = excerpt.strip()

    last_page = data.xpath('//li[@class="page-item"][following-sibling::li[1]/a[contains(., "Fazit")]]/a/text()').string()
    if last_page:
        last_page = int(last_page) + 1

    page = 1
    next_url = data.xpath('//li[@class="page-item"][last()]/a/@href').string()
    if last_page and last_page > page:
        title = review.title + " - Seite " + str(page)
        review.add_property(type='pages', value=dict(title=title, url=review.url))

        session.do(Request(next_url), process_review_next, dict(context, product=product, review=review, page=page+1, last_page=last_page))
    else:
        context['product'] = product
        context['review'] = review
        process_review_next(data: Response, context: dict[str, str], session: Session)


def process_review_next(data: Response, context: dict[str, str], session: Session):
    review = context['review']

    grade_overall = data.xpath('//td[contains(., "Spielspaß")]/following-sibling::td[contains(., "%")]//text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.strip(' %'))
        review.grades.append(Grade(type='overall', value=grade_overall, best=100.0))

    grades = data.xpath('//tr[contains(., "Wertung")]/following-sibling::tr')
    if grades:
        for grade in grades:
            if grade:
                name = grade.xpath('td[1]/text()').string()
                value = grade.xpath('td[contains(., "%")]/text()').string()
                if name and value:
                    if '-' in value:
                        value = '0'

                    value = float(value.strip(' %v'))
                    review.grades.append(Grade(name=name, value=value, best=100.0))

    page = context.get('page', 1)
    if page > 1:
        title = review.title + " - Seite " + str(page)
        url = data.response_url.replace('#start', '')
        review.add_property(type='pages', value=dict(title=title, url=url))

        pros = data.xpath('//div[@class="block" or @class="bigfont block"]/text()[preceding::text()[contains(., "Pro:")]][not(preceding::text()[contains(., "Contra:") or contains(., "Kontra:")])][not(contains(., "Contra:") or contains(., "Kontra:"))]').strings()
        if pros:
            for pro in pros:
                pro = pro.replace('\n', ' ').replace('\t', ' ').strip(' +•-.…')
                if pro:
                    review.add_property(type='pros', value=pro)

        cons = data.xpath('//div[@class="block" or @class="bigfont block"]/text()[preceding::text()[contains(., "Contra:") or contains(., "Kontra:")]][not(contains(., "Contra:") or contains(., "TESTER:") or contains(., "Kontra:"))][not(contains(., "Systeminfo"))][not(contains(., "Features"))][not(preceding::text()[contains(., "Systeminfo") or contains(., "Features")])]').strings()
        if cons:
            for con in cons:
                con = con.replace('\n', ' ').replace('\t', ' ').strip(' -•.…')
                if con:
                    review.add_property(type='cons', value=con)

        if not pros and not cons:
            pros_cons = data.xpath('//div[@class="block" or @class="bigfont block"]//text()[preceding::div[contains(., "Pro und Contra")]][not(contains(., "TESTER:"))][not(contains(., "Systeminfo"))][not(contains(., "Features"))][not(preceding::div[contains(., "Systeminfo") or contains(., "Features")])]').strings()
            if pros_cons:
                for pro_con in pros_cons:
                    if pro_con and '+ ' in pro_con:
                        pro = pro_con.replace('\n', ' ').replace('\t', ' ').strip(' +•-.…')
                        if pro:
                            review.add_property(type='pros', value=pro)

                    elif pro_con and '- ' in pro_con:
                        con = pro_con.replace('\n', ' ').replace('\t', ' ').strip(' +•-.…')
                        if con:
                            review.add_property(type='cons', value=con)

        conclusion = data.xpath('//div[contains(text(), "Fazit:")]/following-sibling::div[1]/text()[not(contains(., "Pro und Contra"))][not(preceding::div[contains(., "Pro und Contra")])]').string(multiple=True)
        if conclusion:
            context['conclusion'] = conclusion.strip()

        excerpt = data.xpath('//div[@class="block" or @class="bigfont block"]/text()[not(contains(., "Pro und Contra"))][not(preceding::div[contains(., "Pro und Contra")])]').string(multiple=True)
        if excerpt and not conclusion:
            context['excerpt'] += " " + excerpt.strip()

    last_page = context.get('last_page', 1)
    next_url = data.xpath('//li[@class="page-item"][last()]/a/@href').string()
    if next_url and int(last_page) > page:
        session.do(Request(next_url), process_review_next, dict(context, page=page+1, last_page=last_page))
    else:
        if context.get('summary'):
            review.add_property(type='summary', value=context['summary'])
        if context.get('conclusion'):
            review.add_property(type='conclusion', value=context['conclusion'])
        if context.get('excerpt'):
            review.add_property(type='excerpt', value=context['excerpt'])

        product = context['product']

        product.reviews.append(review)

        session.emit(product)