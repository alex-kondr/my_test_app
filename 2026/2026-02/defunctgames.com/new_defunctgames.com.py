from agent import *
from models.products import *
import simplejson


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


def run(context, session):
    session.browser.use_new_parser = True
    session.sessionbreakers = [SessionBreak(max_requests=4000)]
    session.queue(Request('http://www.defunctgames.com/', use='curl', force_charset='utf-8'), process_frontpage, dict())


def process_frontpage(data, context, session):
    strip_namespace(data)

    cats = data.xpath('//li[@class="menu-end"]/ul/li')
    for cat in cats:
        name = cat.xpath('a//text()').string(multiple=True).strip()

        subcats = cat.xpath('ul//a')
        if subcats:
            for subcat in subcats:
                subcat_name = subcat.xpath('.//text()').string(multiple=True)
                if subcat_name == name:
                    subcat_name = ''

                cat_group = subcat.xpath('@href').string().split('/')[-1]
                url = 'http://www.defunctgames.com/ajax/filter_reviews.php?system={}&limit=20&page=1'.format(cat_group)
                session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name+'|'+subcat_name, cat_group=cat_group))
        else:
            cat_group = cat.xpath('a/@href').string().split('/')[-1]
            url = 'http://www.defunctgames.com/ajax/filter_reviews.php?system={}&limit=20&page=1'.format(cat_group)
            session.queue(Request(url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(cat=name, cat_group=cat_group))


def process_revlist(data, context, session):
    strip_namespace(data)

    data_json = simplejson.loads(data.content)

    revs = data_json.get('reviews')
    for rev in revs:
        title = rev.get('title')
        ssid = rev.get('show_id')
        url = 'http://www.defunctgames.com' + rev.get('link')
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(context, title=title, ssid=ssid, url=url))

    page_cnt = context.get('page_cnt', data_json.get('pagination', {}).get('total_pages'))
    next_page = context.get('page', 1) + 1
    if next_page <= page_cnt:
        next_url = 'http://www.defunctgames.com/ajax/filter_reviews.php?system={cat_group}&limit=20&page={page}'.format(cat_group=context['cat_group'], page=next_page)
        session.queue(Request(next_url, use='curl', force_charset='utf-8', max_age=0), process_revlist, dict(context, page=next_page, page_cnt=page_cnt))


def process_review(data, context, session):
    strip_namespace(data)

    product = Product()
    product.name = context['title']
    product.url = context['url']
    product.ssid = context['ssid']
    product.category = context['cat'].replace('(Reviews)', '').replace('OTHER CONSOLES', '').strip(' |').title()
    product.manufacturer = data.xpath('//div[@class="review-card__developer"]/ul//text()').string(multiple=True)

    genre = data.xpath('//div[@class="review-card__genre"]/ul//text()').string(multiple=True)
    if genre:
        product.category += '|' + genre

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid
    review.date = data.xpath('//time/@datetime').string()

    author = data.xpath('//p[@class="review__author"]/a/text()').string()
    author_url = data.xpath('//p[@class="review__author"]/a/@href').string()
    if author and author_url:
        author_ssid = author_url.split('@')[0].replace('mailto:', ''). strip()
        review.authors.append(Person(name=author, ssid=author_ssid))
    elif author:
        review.authors.append(Person(name=author, ssid=author))

    grade_overall = data.xpath('//li[@class="review-score-grade"]/a/@href').string()
    if grade_overall:
        grade_overall = grade_overall.split('/')[-1]
        if grade_overall and float(grade_overall) > 0:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=100.0))

    excerpt = data.xpath('//div[@class="review__text" and not(.//b[contains(., "Warning")])]//text()').string(multiple=True)
    if excerpt:
        if 'Conclusion: ' in excerpt:
            excerpt, conclusion = excerpt.split('Conclusion: ')
            review.add_property(type='conclusion', value=conclusion.strip())

        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
