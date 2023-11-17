from agent import *
from models.products import *
import simplejson

XCATS = ['Fan Shop']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=10000)]
    session.queue(Request("https://www.scheels.com/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="has-children tier-1"]')
    for cat in cats:
        name = cat.xpath('a//text()').string()

        sub_cats = cat.xpath('ul/li[@class="tier-2 has-children"]')
        if name not in XCATS:
            for sub_cat in sub_cats:
                sub_name = sub_cat.xpath('a//text()').string()

                sub_cats1 = sub_cat.xpath('ul/li[@class="has-children third-level tier-3"]')
                if sub_cats1:
                    for sub_cat1 in sub_cats1:
                        sub_name1 = sub_cat1.xpath('a//text()').string()

                        sub_cats2 = sub_cat1.xpath('ul/li[@class="tier-4"]/a')
                        if sub_cats2:
                            for sub_cat2 in sub_cats2:
                                sub_name2 = sub_cat2.xpath('text()').string()
                                url = sub_cat2.xpath('@href').string()
                                session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1 + '|' + sub_name2))
                        else:
                            url = sub_cat1.xpath('a/@href').string()
                            session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name + '|' + sub_name1))
                else:
                    url = sub_cat.xpath('a/@href').string()
                    session.queue(Request(url), process_prodlist, dict(cat=name + '|' + sub_name))


def process_prodlist(data, context, session):
    prods = data.xpath('//div[@class="product-tile"]')
    for prod in prods:
        product = Product()
        product.category = context['cat']
        product.name = prod.xpath('@data-itemname').string()
        product.ssid = prod.xpath('@data-uuid').string()
        product.sku = prod.xpath('@data-itemid').string()
        product.url = prod.xpath('.//div[@class="product-image"]//a/@href').string()

        revs_url = 'https://cdn-ws.turnto.com/v5/sitedata/TXOE2FrZzlhkSdesite/{}/d/review/en_US/0/9999/%7B%7D/RECENT/false/false/'.format(product.sku)
        revs_count = prod.xpath('(following::div[@class="TTteaser"])[1]/@data-reviewcount').string()
        if revs_count != "0":
            session.queue(Request(revs_url), process_reviews, dict(product=product, url=revs_url))

    next_url = data.xpath('//a[@class="page-next button is-primary"]/@href').string()
    if next_url:
        session.queue(Request(next_url), process_category, dict(context))


def process_reviews(data, context, session):
    product = context['product']

    revs_json = simplejson.loads(data.content)
    revs = revs_json['reviews']
    for rev in revs:
        review = Review()
        review.url = context['url']
        review.type = 'user'
        review.ssid = str(rev['id'])
        review.date = rev['dateCreatedFormatted']

        title = rev['title']
        if title and title != "" and title.isspace() != True:
            title = title.encode("ascii", errors="ignore")
            review.title = title

        if rev['user']['firstName'] and rev['user']['lastName']:
            author = rev['user']['firstName'] + " " + rev['user']['lastName']
        else:
            author = rev['user']['nickName']
            
        author_ssid = rev['user']['id']
        if not author_ssid:
            author_ssid = author.encode("ascii", errors="ignore")
        
        if not author_ssid:
            continue

        if author and author.isspace() != True:
            author = author.encode("ascii", errors="ignore")
            review.authors.append(Person(name=author, ssid=str(author_ssid)))

        is_verified = rev['purchaseDateFormatted']
        if is_verified != "":
            review.add_property(type='is_verified_buyer', value=True)

        is_recommended = rev['recommended']
        if is_recommended == "true":
            review.add_property(type='is_recommended', value=True)

        hlp_yes = rev['upVotes']
        if hlp_yes:
            review.add_property(type='helpful_votes', value=int(hlp_yes))
        
        hlp_no = rev['downVotes']
        if hlp_no:
            review.add_property(type='not_helpful_votes', value=int(hlp_no))

        grade_overall = rev['rating']
        if grade_overall:
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))

        excerpt = rev['text'].encode("ascii", errors="ignore").replace('<br />', '')        
        if excerpt and excerpt != "" and excerpt.isspace() != True:
            review.add_property(type='excerpt', value=excerpt)

            product.reviews.append(review)
    
    # No next page, load 9999 reviews

    if product.reviews:
        session.emit(product)
