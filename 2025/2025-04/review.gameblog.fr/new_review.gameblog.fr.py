from agent import *
from models.products import *
import simplejson
import re


def remove_emoji(string):
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               u"\U00002500-\U00002BEF"  # chinese char
                               u"\U00002702-\U000027B0"
                               u"\U00002702-\U000027B0"
                               u"\U000024C2-\U0001F251"
                               u"\U0001f926-\U0001f937"
                               u"\U00010000-\U0010ffff"
                               u"\u2640-\u2642"
                               u"\u2600-\u2B55"
                               u"\u200d"
                               u"\u23cf"
                               u"\u23e9"
                               u"\u231a"
                               u"\ufe0f"  # dingbats
                               u"\u3030"
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)


def run(context, session):
    url = 'https://www.gameblog.fr/api/posts/load_more_posts/route/list_page/controller/components_controller/method/search_post_items/view_mode/full/sort_order/desc/offset/0/ppp/10/release_filter/a-venir/search_filters/Tech%2CHardware%20Tests%2Call%2Call%2C%2C%2C%2C%2C%2C%2C%2C%2C/limit/gameblog'
    session.queue(Request(url, force_charset='utf-8'), process_revlist, {})


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="item-content-header"]')
    if not revs:
        return

    for rev in revs:
        title = rev.xpath('h2[@class="title"]/text()').string()
        url = rev.xpath('a[contains(@class, "title")]/@href').string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(title=title, url=url))

    offset = context.get('offset', 0) + 10
    next_url = 'https://www.gameblog.fr/api/posts/load_more_posts/route/list_page/controller/components_controller/method/search_post_items/view_mode/full/sort_order/desc/offset/{}/ppp/10/release_filter/a-venir/search_filters/Tech%2CHardware%20Tests%2Call%2Call%2C%2C%2C%2C%2C%2C%2C%2C%2C/limit/gameblog'.format(offset)
    session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict(offset=offset))


def process_review(data, context, session):
    product = Product()
    product.name = data.xpath('//h3[contains(@class, "title ")]/a/text()').string() or context['title'].split('TEST de ')[-1].split('TEST ')[-1].split(' : ', 1)[0].replace('Notre Test !', '').replace('Test Du', '').replace('La Test', '').strip().title()
    product.url = context['url']
    product.ssid = product.url.split('-')[-1]
    product.manufacturer = data.xpath('//div[@class="developers"]/span/a/text()').string()

    platforms = data.xpath('//div[@class="platforms"]/div/a/text()').strings()
    product.category = '/'.join({platform.strip() for platform in platforms if platform.strip()})
    if not product.category:
        product.category = 'Tech'

    review = Review()
    review.title = context['title']
    review.url = context['url']
    review.ssid = product.ssid
    review.type = 'pro'

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    author = data.xpath('//a[@class="name"]/text()').string()
    author_url = data.xpath('//a[@class="name"]/@href').string()
    if author and author_url:
        author_ssid = author_url.split('/')[-1]
        review.authors.append(Person(name=author, profile_url=author_url, ssid=author_ssid))

    pros = data.xpath('(//tr[contains(., "ON A AIMÉ")]/following-sibling::tr//ul)[1]/li')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('…', '').strip(' .\n\t+-')
        if pro:
            review.add_property(type='pros', value=pro)

    cons = data.xpath('''(//tr[contains(., "ON N'A PAS AIMÉ")]/following-sibling::tr//ul)[2]/li''')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('…', '').strip(' .\n\t+-')
        if con:
            review.add_property(type='cons', value=con)

    summary = data.xpath('//div[@class="post-excerpt"]/p//text()').string(multiple=True)
    if summary:
        summary = remove_emoji(summary).strip()
        review.add_property(type="summary", value=summary)

    conclusion = data.xpath('//tr/td/p[normalize-space(text())]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type="conclusion", value=conclusion)

    excerpt = data.xpath('//div[@class="post-content"]/p//text()').string(multiple=True)
    if excerpt:
        excerpt = remove_emoji(excerpt).strip()
        review.add_property(type="excerpt", value=excerpt)

        next_url = 'https://www.gameblog.fr/v5/review_summary_component?ct=content_block_8&user_presence=false&id={}&spf=load&incoming_page_type=review_page'.format(product.ssid)
        session.do(Request(next_url, force_charset='utf-8', max_age=0), process_review_next, dict(review=review, product=product))


def process_review_next(data, context, session):
    review = context['review']

    new_data = simplejson.loads(data.content).get('body', {}).get('content_block_8')
    new_data = data.parse_fragment(new_data)

    grade_overall = new_data.xpath('//text[@class="rating-text"]/text()').string()
    if grade_overall and grade_overall.isdigit():
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))

    pros = new_data.xpath('//div[@class="good-points"]//div[@class="point"]')
    for pro in pros:
        pro = pro.xpath('.//text()').string(multiple=True).replace('…', '').strip(' .\n\t+-')
        if pro:
            review.add_property(type='pros', value=pro)

    cons = new_data.xpath('//div[@class="bad-points"]//div[@class="point"]')
    for con in cons:
        con = con.xpath('.//text()').string(multiple=True).replace('…', '').strip(' .\n\t+-')
        if con:
            review.add_property(type='cons', value=con)

    conclusion = new_data.xpath('//div[@class="review-text"]//text()').string(multiple=True)
    if conclusion:
        conclusion = remove_emoji(conclusion).strip()
        review.add_property(type="conclusion", value=conclusion)

    product = context['product']
    product.reviews.append(review)

    session.emit(product)
