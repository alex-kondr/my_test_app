from agent import *
from models.products import *


X_PROS_CONS = ['None.', 'none.', 'None', 'none', 'N/a']
X_CATS = ['Analytics Business Intelligence', 'Cloud', 'Collaboration', 'Department and Industry Specific', 'Development Environment', 'HR Software (HCM)', 'IT Management Software', 'IT Service', 'Middleware and Database', 'Operating System', 'Sales and Marketing Software', 'Vendor', 'Virtualization']
X_SUBCATS = ['Other Fun Products', 'Online Music', 'DNS Provider', 'Domain Registrar', 'Internet Service Provider (ISP)', 'Telco', 'VOIP', 'Video Conferencing', 'Firewall', 'Authentication, Authorization and Accounting (AAA)', 'Cloud Security', 'Computer Security', 'Cybersecurity', 'Data Loss Prevention (DLP)', 'Email Security', 'Network Security', 'Security Information and Event Management (SIEM)', 'Converged Infrastructure (CI)', 'Server', 'Server Cabinet', 'Wire Management', 'Copy Utility', 'Data Backup', 'Disk Usage', 'Document Generation Software', 'File Archive Software', 'File Management Software', 'File Recovery', 'File Transfer']


def run(context, session):
    session.sessionbreakers = [SessionBreak(max_requests=9000)]
    session.queue(Request("https://community.spiceworks.com/products/"), process_catlist, dict())


def process_catlist(data, context, session):
    cats = data.xpath('//li[@class="sui-dropdown_entry"]')
    for cat in cats:
        url = cat.xpath('a/@href').string()
        name = cat.xpath('a//text()').string()
        if name not in X_CATS:
            session.queue(Request(url), process_subcats, dict(cat=name))


def process_subcats(data, context, session):
    subcats = data.xpath('//li[@class="category_children-item"]')
    for subcat in subcats:
        url = subcat.xpath('a/@href').string() + "?&sort=highest_rated"
        name = subcat.xpath('a//text()').string()
        if name[-3] == "(":
            name = name[:-4:]
        elif name[-4] == "(":
            name = name[:-5:]
        elif name[-5] == "(":
            name = name[:-6:]
        elif name[-6] == "(":
            name = name[:-7:]
        if name not in X_SUBCATS:
            session.queue(Request(url), process_prodlist, dict(context, cat=context['cat']+'|'+name))


def process_prodlist(data, context, session):
    revs_on_next_page = True

    prods = data.xpath('//div[@class="product-header"]')
    for prod in prods:
        rating = prod.xpath('.//div[@class="product-header__rating"]/text()').string()
        if rating == "No reviews yet!":
            revs_on_next_page = False
            break

        product = Product()
        product.category = context['cat']
        product.name = prod.xpath('.//div[@class="product-header__header"]/div/a/text()').string()
        product.url = prod.xpath('.//div[@class="product-header__header"]/div/a/@href').string()
        product.ssid = product.url.split('/')[-1].split('-')[0]
        product.manufacturer = prod.xpath('.//div[@class="product-header__manufacturer"]/span//text()').string()

        revs_url = product.url + "/reviews"
        session.do(Request(revs_url), process_review, dict(product=product, url=revs_url))

        if product.reviews:
            session.emit(product)

    next_url = data.xpath('//a[@class="sui-next"]/@href').string()
    if next_url and revs_on_next_page == True:
        session.do(Request(next_url), process_prodlist, dict(context))
    

def process_review(data, context, session):
    product = context['product']

    revs = data.xpath('//article[@class="product-review "]')
    for rev in revs:
        review = Review()
        review.title = rev.xpath('(parent::*/following::body)[1]//h5[@class="product-review-content__title"]//text()').string()
        review.url = context['url']
        review.ssid = rev.xpath('@id').string().split('-')[-1]
        review.type = 'user'
        review.date = rev.xpath('(parent::*/following::body)[1]//div[@class="product-review-content__date"]//text()').string()

        is_recommended = rev.xpath('(parent::*/following::body)[1]/div[@class="product-review-details__recommendation"]')
        if is_recommended:
            review.add_property(type='is_recommended', value=True)

        is_verified = rev.xpath('following-sibling::*//h5[@class="verified-professional-popover_content-header"]')
        if is_verified:
            review.add_property(type='is_verified_buyer', value=True)

        author = rev.xpath('following-sibling::*//span[@class="product-review-author-info__name-link"]//text()').string()
        if author:
            author_url = rev.xpath('following-sibling::*//a[contains(@class, "-link")]/@href').string()
            author_ssid = author_url.split('/')[-1]
            review.authors.append(Person(name=author, url=author_url, ssid=author_ssid))
        if not author:
            author = rev.xpath('following-sibling::*//span[@class="product-review-author-info__name-no-link"]//text()').string()
            if author:
                review.authors.append(Person(name=author, ssid=author))

        grade_overall = rev.xpath('following-sibling::*//span[@class="stars"]/@aria-label').string()
        if grade_overall:
            grade_overall = grade_overall.split(' ')[0]
            review.grades.append(Grade(type='overall', value=float(grade_overall), best=5.0))
        
        pros = rev.xpath('(parent::*/following::body)[1]//h6[contains(text(), "What are the pros?")]/following-sibling::div[1]/p/text()').string(multiple=True)
        if pros and pros not in X_PROS_CONS:
            review.add_property(type="pros", value=pros)
        
        cons = pros = rev.xpath('(parent::*/following::body)[1]//h6[contains(text(), "What are the cons?")]/following-sibling::div/p//text()').string(multiple=True)
        if cons and cons not in X_PROS_CONS:
                review.add_property(type="cons", value=cons)
        
        excerpt = rev.xpath('(parent::*/following::body)[1]//div[@class="product-review-content__main-text"]/p//text()').string(multiple=True)
        if excerpt:
            review.add_property(type='excerpt', value=excerpt)
            product.reviews.append(review)
    
    next_url = data.xpath('//a[@class="sui-next"]/@href').string()
    if next_url:
        session.do(Request(next_url), process_review, dict(context, product=product))
