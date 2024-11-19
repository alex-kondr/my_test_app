from agent import *
from models.products import *


CONCLUSION_WORDS = ['In the end, ', 'In conclusion, ', 'Overall, ']
PLATFORMS = ['Xbox One', 'PS4', 'PC', 'Xbox', 'iOS', 'Nintendo Switch', 'PlayStation VR', '3DS']


def run(context, session):
    session.queue(Request('http://www.biogamergirl.com/search/label/Video%20Game%20Reviews', force_charset='utf-8'), process_revlist, dict())


def process_revlist(data, context, session):
    revs = data.xpath("//div[@class='post-outer']/div[@class='post']")
    for rev in revs:
        author = rev.xpath('.//a[@class="g-profile"]').first()
        author_name = author.xpath('@title').string()
        author_url = author.xpath('@href').string()

        url = rev.xpath(".//h2/a/@href").string()
        if 'watch-dogs-PS3-video-game-review' in url:
            continue

        title = rev.xpath(".//h2/a//text()").string()
        summary = rev.xpath(".//div[@class='resumo']/span/text()").string()
        session.queue(Request(url, use='curl', force_charset='utf-8'), process_review, dict(url=url, title=title, summary=summary, author_name=author_name, author_url=author_url))

    next_url = data.xpath("//a[@id='Blog1_blog-pager-older-link']/@href").string()
    if next_url:
        session.queue(Request(next_url, force_charset='utf-8'), process_revlist, dict())


def process_review(data, context, session):
    product = Product()

    product.name = context['title']
    if ' (Video' in product.name:
        product.name = product.name.split(' (')[0]
    elif 'Review:' in product.name:
        product.name = product.name.split('Review: ')[-1]
    else:
        product.name = product.name.replace('Review ', '')

    product.ssid = context['url'].split('/')[-1].replace('.html', '')

    product.url = data.xpath('//a[contains(., "website")]/@href').string()
    if not product.url:
        product.url = data.xpath('//a[contains(@href, "store.steampowered")]/@href').string()
    if not product.url:
        product.url = context['url']

    product.url = product.url.split('%5D')[-1]

    category = 'Games'
    cats = data.xpath('//div[@class="label-head"]//a/text()')
    if cats:
        for cat in cats:
            cat_name = cat.string()
            if cat_name == 'Tech Review':
                category = 'Tech'
                break

            if cat_name in PLATFORMS:
                category += '|' + cat_name
    product.category = category

    review = Review()
    review.title = context['title']
    review.ssid = product.ssid
    review.type = 'pro'
    review.url = context['url']

    date = data.xpath('.//abbr/@title')
    if date:
        review.date = date.string().split('T')[0]

    author_name = context['author_name']
    author_url = context.get('author_url')
    if author_url and "biogamergirl.com/" not in author_url:
        review.authors.append(Person(name=author_name, profile_url=author_url, ssid=author_name))
    else:
        review.authors.append(Person(name=author_name, ssid=author_name))

    grade = data.xpath('//div[@class="hreview"]/parent::body//span[contains(., " out of ")]//text()').string(multiple=True)
    if not grade:
        grade = data.xpath("//b[contains(.,'out of')]//text()").string(multiple=True)
    if not grade:
        grade = data.xpath("//span[contains(.,' out ')]//text()").string(multiple=True)

    if grade:
        grade_overall = grade.split(':')[-1].split(' out ')[0]
        grade_max = grade.split(':')[-1].split(' out ')[1].split(' Reviewed')[0].split('of ')[-1].split(' ')[0]
        review.grades.append(Grade(type='overall', value=float(grade_overall), best=float(grade_max)))

    summary = context.get('summary')
    if summary and '...' not in summary:
        summary = ' '.join(summary.split())
        review.properties.append(ReviewProperty(type='summary', value=summary))

    excerpt = data.xpath('//div[@class="hreview"]/parent::body//text()').string(multiple=True)
    if excerpt:
        if summary and summary in excerpt:
            excerpt = excerpt.split(summary)[-1]
        if 'Score:' in excerpt:
            excerpt = excerpt.split('Score: ')[0]
        else:
            excerpt = excerpt.split('SCORE: ')[0]

        if 'Game Information:' in excerpt:
            excerpt = excerpt.split('Game Information:')
            if 'Developer & Publisher:' in excerpt[1]:
                product.manufacturer = excerpt[1].split('Developer & Publisher:')[-1].split('Platforms:')[0].split('Available')[0].split('Distributor:')[0]
            elif 'Developer:' in excerpt[1]:
                product.manufacturer = excerpt[1].split('Developer:')[-1].split('Publisher:')[0].split('Platforms:')[0].split('Distributor:')[0].split('Available')[0]

            excerpt = excerpt[0]

        for word in CONCLUSION_WORDS:
            if word in excerpt:
                conclusion = excerpt.split(word)[-1]
                conclusion = conclusion.split('Game Features:')[0].split('Features:')[0].split('FEATURES:')[0].split('GAMEPLAY FEATURES')[0].split('To learn more,')[0].split('If you want to learn more')[0].split('If you would like to learn more')[0].split('If you would like to try the game yourself,')[0]
                excerpt = excerpt.split(word)[0]
                review.properties.append(ReviewProperty(type='conclusion', value=conclusion))
                break

        excerpt = excerpt.split('Game Features: ')[0].split('Features:')[0].split('FEATURES:')[0].split('To learn more,')[0].split('If you want to learn more')[0].split('If you would like to learn more')[0].split('To learn more visit')[0]

        review.properties.append(ReviewProperty(type='excerpt', value=excerpt.strip()))

        product.reviews.append(review)

        session.emit(product)
