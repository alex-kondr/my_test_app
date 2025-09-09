from agent import *
from models.products import *
import re


X_REVS = ['https://p3.no/filmpolitiet-dlc', 'https://p3.no/filmpolitiet-podkast/#filmpolitiets-got-pod---episode-4', 'https://p3.no/filmpolitiet/norges-beste-tv-serier-2000-tallet']


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
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request('https://p3.no/category/tv/'), process_revlist, dict(cat='TV-serier'))
    session.queue(Request('https://p3.no/category/film/'), process_revlist, dict(cat='Film'))
    session.queue(Request('https://p3.no/category/spill/'), process_revlist, dict(cat='Spill'))


def process_revlist(data, context, session):
    revs = data.xpath('//div[@class="archive-grid"]/h2//a')
    for rev in revs:
        title = remove_emoji(rev.xpath('text()').string())
        url = rev.xpath('@href').string().strip('/')
        if 'p3.no' in url and url not in X_REVS:
            session.queue(Request(url), process_review, dict(context, title=title, url=url))

    next_url = data.xpath('//div[@class="post-previous"]//a/@href').string()
    if next_url:
        session.queue(Request(next_url), process_revlist, dict(context))


def process_review(data, context, session):
    if data.xpath('//p//img[contains(@src, "topp_1")]'):
        return  # Multi-revs. There full reviews for any product on site

    product = Product()
    product.name = data.xpath('//div[@class="review-info"]/h3/text()').string() or context['title']
    product.url = context['url']
    product.ssid = data.xpath('//div[contains(@class, "surrogate")]/@data-id').string()
    product.category = context['cat']
    product.manufacturer = data.xpath('//div[p[@class="secondary"]]/p[@class][last()]/text()').string()

    product.category = context['cat']
    genres = data.xpath('//div[p[@class="secondary"]]/p[not(@class)]/text()').string()
    if genres:
        product.category += '|' + genres.replace(', ', '/')

    review = Review()
    review.type = 'pro'
    review.title = context['title']
    review.url = product.url
    review.ssid = product.ssid

    date = data.xpath('//meta[@property="article:published_time"]/@content').string()
    if date:
        review.date = date.split('T')[0]

    authors = data.xpath('//a[@class="author__name"]')
    for author in authors:
        author_name = author.xpath('text()').string(multiple=True)
        author_url = author.xpath("@href").string()
        if author_name and author_url:
            author_ssid = author_url.strip('/').split()[-1]
            review.authors.append(Person(name=author_name, ssid=author_ssid))
        elif author_name:
            review.authors.append(Person(name=author_name, ssid=author_name))

    grade_overall = data.xpath('//div[contains(@class, "article-lead")]//span[@class="review-rating"]/span/text()').string()
    if grade_overall:
        grade_overall = float(grade_overall.split()[-1])
        review.grades.append(Grade(type='overall', value=grade_overall, best=6.0))

    summary = data.xpath('//div[contains(@class, "article-lead")]/p[not(@class)]//text()').string(multiple=True)
    if summary:
        review.add_property(type='summary', value=summary)

    conclusion = data.xpath('(//h2|//h3|//h5)[contains(., "Konklusjon")]/following-sibling::p//text()').string(multiple=True)
    if conclusion:
        review.add_property(type='conclusion', value=conclusion)

    excerpt = data.xpath('//div[contains(@class,"article-body")]/p[not(preceding-sibling::h2[regexp:test(.,"Konklusjon")])][not(contains(., "(Anmeldelsen fortsetter under bildet)") or regexp:test(., "anmeldelse:", "i"))]//text()[not(contains(., "[youtube"))][not(parent::strong) and not(contains(text(), "Spoileradvarsel!") or contains(., "href="))]').string(multiple=True)
    if excerpt:
        if conclusion:
            excerpt = excerpt.replace(conclusion, '')

        excerpt = remove_emoji(excerpt.encode('utf-8')).strip()
        review.add_property(type='excerpt', value=excerpt)

        product.reviews.append(review)

        session.emit(product)
