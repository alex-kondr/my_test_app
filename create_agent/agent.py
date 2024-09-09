from pathlib import Path
from enum import Enum


class ProcessRun(Enum):
    frontpage = "frontpage"
    revlist = "revlist"



class AgentForm:
    def __init__(self, name: str):
        self.name = name
        self.agent_dir = Path(self.name)
        self.agent_dir.mkdir(exist_ok=True)
        self.file_path = self.agent_dir / Path("new_" + self.name + ".py")
        self.funcs = {
            "frontpage": self.create_frontpage,
            "revlist": self.create_revlist,
            # "prodlist": self.create_prodlist,
            "product": self.create_product,
            "review": self.create_review,
            "reviews": self.create_reviews,
        }

    def create_run(
        self,
        name_agent_for_test: str,
        agent_id: str,
        url: str,
        next_func: ProcessRun,
        new_parser: bool,
        breakers: str,
        curl: bool
        ):

        self.create_test_file(name_agent_for_test, agent_id)

        text = (
            "from agent import *\n"
            "from models.products import *\n\n\n"
            "def run(context, session):\n"
        )

        text += "    session.browser.use_new_parser = True\n" if new_parser else ""
        text += f"    session.sessionbreakers = [SessionBreak(max_requests={breakers})]\n" if breakers else ""
        text += """    session.queue(Request('{url}'{curl}), process_{next_func}, dict())\n""".format(url=url, next_func=next_func, curl=", use='curl'" if curl else "")

        with open(str(self.file_path).replace("new_", "old_"), "w", encoding="utf-8"): pass
        with open(self.file_path, "w", encoding="utf-8") as file:
            file.write(text)

        # self.funcs.get(next_func)()

    def create_frontpage(
        self,
        cats_xpath: str,
        name_xpath: str,
        url_xpath: str
        ):
        text = (
            "\n\ndef process_frontpage(data, context, session):\n"
            f"    cats = data.xpath('{cats_xpath}')\n"
            "    for cat in cats:\n"
            f"        name = cat.xpath('{name_xpath}').string()\n"
            f"        url = cat.xpath('{url_xpath}').string()\n"
            "        session.queue(Request(url), process_revlist, dict(cat=name))\n"
        )

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(text)

        # self.create_revlist()

    def create_revlist(
        self,
        revs_xpath: str,
        name_title: str,
        name_title_xpath: str,
        url_xpath: str,
        prod_rev: str,
        next_url_xpath: str
        ):

        # text = "\n\ndef process_prodlist"

        text = (
            "\n\ndef process_revlist(data, context, session):\n"
            f"    revs = data.xpath('{revs_xpath}')\n"
            "    for rev in revs:\n"
            f"        {name_title} = rev.xpath('{name_title_xpath}').string()\n"
            f"        url = rev.xpath('{url_xpath}').string()\n"
            f"        session.queue(Request(url), process_{prod_rev}, dict({name_title}={name_title}, url=url))\n"
            f"\n    next_url = data.xpath('{next_url_xpath}').string()\n"
            "    if next_url:\n"
            "        session.queue(Request(next_url), process_revlist, dict())\n"
        )

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(text)

        # self.funcs.get(prod_rev)()

    def create_product(self):
        manufacturer_xpath = input("manufacturer_xpath?: ")
        sku_xpath = input("sku_xpath?: ")
        mpn_xpath = input("mpn_xpath?: ")
        ean_xpath = input("ean_xpath?: ")

        text = (
            "\n\ndef process_product(data, context, session):\n"
            "    product = Product()\n"
            "    product.name = context['name']\n"
            "    product.url = context['url']\n"
            "    product.ssid = product.url.split('/')[-2]\n"
            "    product.category = context['cat']\n"
        )

        text += (
            f"    product.manufacturer = data.xpath('{manufacturer_xpath}').string()\n"
        ) if manufacturer_xpath else ""

        text += (
            f"    product.sku = data.xpath('{sku_xpath}').string()\n"
        ) if sku_xpath else ""

        text += (
            f"\n    mpn = data.xpath('{mpn_xpath}').string()\n"
            "    if mpn:\n"
            "        product.add_property(type='id.manufacturer', value=mpn)\n"
        ) if mpn_xpath else ""

        text += (
            f"\n    ean = data.xpath('{ean_xpath}').string()\n"
            "    if ean:\n"
            "        product.add_property(type='id.ean', value=ean)\n"
        ) if ean_xpath else ""

        text += (
            "\n    context['product'] = product\n"
            "    process_reviews(data, context, session)\n"
        )

        self.create_reviews()

    def create_review(
        self,
        date_xpath: str,
        author_xpath: str,
        author_url_xpath: str,
        grade_overall_xpath: str,
        pros_xpath: str,
        cons_xpath: str,
        summary_xpath: str,
        conclusion_xpath: str,
        excerpt_with_concl_xpath: str,
        excerpt_xpath: str,
        ):

        text = (
            "\n\ndef process_review(data, context, session):\n"
            "    product = Product()\n"
            "    product.name = context['title'].replace('', '').strip()\n"
            "    product.url = context['url']\n"
            "    product.ssid = product.url.split('/')[-2]\n"
            "    product.category = 'Tech'\n"
            "\n    review = Review()\n"
            "    review.type = 'pro'\n"
            "    review.title = context['title']\n"
            "    review.url = product.url\n"
            "    review.ssid = product.ssid\n"
            f"\n    date = data.xpath('{date_xpath}').string()\n"
            "    if date:\n"
            "        review.date = date.split('T')[0]\n"
        )

        text += (
            f"\n    author = data.xpath('{author_xpath}').string()\n"
            f"    author_url = data.xpath('{author_url_xpath}').string()\n"
            "    if author and author_url:\n"
            "        author_ssid = author_url.split('/')[-1]\n"
            "        review.authors.append(Person(name=author, ssid=author_ssid, profile_url=author_url))\n"
            "    elif author:\n"
            "        review.authors.append(Person(name=author, ssid=author))\n"
        ) if author_xpath else ""

        text += (
            f"\n    grade_overall = data.xpath('{grade_overall_xpath}').string()\n"
            "    if grade_overall:\n"
            "        review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))\n"
        ) if grade_overall_xpath else ""

        text += (
            f"\n    pros = data.xpath('{pros_xpath}')\n"
            "    for pro in pros:\n"
            "        pro = pro.xpath('.//text()').string(multiple=True)\n"
            "        review.add_property(type='pros', value=pro)\n"
            f"\n    cons = data.xpath('{cons_xpath}')\n"
            "    for con in cons:\n"
            "        con = con.xpath('.//text()').string(multiple=True)\n"
            "        review.add_property(type='cons', value=con)\n"
        ) if pros_xpath else ""

        text += (
            f"\n    summary = data.xpath('{summary_xpath}').string(multiple=True)\n"
            "    if summary:\n"
            "        review.add_property(type='summary', value=summary)\n"
        ) if summary_xpath else ""

        text += (
            f"\n    conclusion = data.xpath('{conclusion_xpath}').string(multiple=True)\n"
            "    if conclusion:\n"
            "        review.add_property(type='conclusion', value=conclusion)\n"
        ) if conclusion_xpath else ""

        text += (
            f"\n    excerpt = data.xpath('{excerpt_with_concl_xpath}').string(multiple=True)\n"
            "    if not excerpt:\n"
            f"        excerpt = data.xpath('{excerpt_xpath}').string(multiple=True)\n"
            "\n    if excerpt:\n"
            "        review.add_property(type='excerpt', value=excerpt)\n"
            "\n        product.reviews.append(review)\n"
            "\n        session.emit(product)\n"
        )

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(text)

    def create_reviews(self):
        revs_xpath = input("revs_xpath: ")
        date_xpath = input("date_xpath: ")
        author_xpath = input("author_xpath?: ")
        grade_overall_xpath = input("grade_overall_xpath?: ")
        pros_xpath = input("pros_xpath?: ")
        cons_xpath = input("cons_xpath?: ")
        summary_xpath = input("summary_xpath?: ")
        conclusion_xpath = input("conclusion_xpath?: ")
        title_xpath = input("title_xpath?: ")
        excerpt_xpath = input("excerpt_xpath: ")
        rev_ssid_xpath = input("rev_ssid_xpath: ")

        text = (
            "\n\ndef process_reviews(data, context, session):\n"
            "    product = context['product']\n"
            f"\n    revs = data.xpath('{revs_xpath}')\n"
            "    for rev in revs:\n"
            "\n        review = Review()\n"
            "        review.type = 'user'\n"
        )

        text += (
            "        review.url = product.url\n"
            f"\n        date = rev.xpath('{date_xpath}').string()\n"
            "        if date:\n"
            "            review.date = date.split('T')[0]\n"
        )

        text += (
            f"\n        author = rev.xpath('{author_xpath}').string()\n"
            "        if author:\n"
            "            review.authors.append(Person(name=author, ssid=author))\n"
        ) if author_xpath else ""

        text += (
            f"\n        grade_overall = rev.xpath('{grade_overall_xpath}').string()\n"
            "        if grade_overall:\n"
            "            review.grades.append(Grade(type='overall', value=float(grade_overall), best=10.0))\n"
        ) if grade_overall_xpath else ""

        text += (
            f"\n        pros = rev.xpath('{pros_xpath}')\n"
            "        for pro in pros:\n"
            "            pro = pro.xpath('.//text()').string(multiple=True)\n"
            "            review.add_property(type='pros', value=pro)\n"
            f"\n        cons = rev.xpath('{cons_xpath}')\n"
            "        for con in cons:\n"
            "            con = con.path('.//text()').string(multiple=True)\n"
            "            review.add_property(type='cons', value=con)\n"
        ) if pros_xpath else ""

        text += (
            f"\n        summary = rev.xpath('{summary_xpath}').string(multiple=True)\n"
            "        if summary:\n"
            "            review.add_property(type='summary', value=summary)\n"
        ) if summary_xpath else ""

        text += (
            f"\n        conclusion = rev.xpath('{conclusion_xpath}').string(multiple=True)\n"
            "        if conclusion:\n"
            "            review.add_property(type='conclusion', value=conclusion)\n"
        ) if conclusion_xpath else ""

        text += (
            f"\n        title = rev.xpath('{title_xpath}').string(multiple=True)\n"
            f"        excerpt = rev.xpath('{excerpt_xpath}').string(multiple=True)\n"
            "        if excerpt:\n"
            "            review.title = title\n"
            "        else:\n"
            "            excerpt = title\n"
            "\n        if excerpt:\n"
            "            review.add_property(type='excerpt', value=excerpt)\n"
            f"\n            review.ssid = rev.xpath('{rev_ssid_xpath}').string()\n"
            "            if not review.ssid:\n"
            "                review.ssid = review.digest() if author else review.digest(excerpt)"
            "\n              product.reviews.append(review)\n"
            "\n        if product.reviews:"
            "            session.emit(product)\n"
        )

        with open(self.file_path, "a", encoding="utf-8") as file:
            file.write(text)

    def create_test_file(self, name_agent_for_test: str, agent_id: str):
        name_agent_for_test = name_agent_for_test.upper().replace(" [", "_").replace("[", "_").replace("]", "").replace(".", "_").replace("-", "_")

        with open("create_agent/test_template.txt", "r", encoding="utf-8") as file:
            test_template = file.read()

        with open(self.agent_dir / Path("test.py"), "w", encoding="utf-8") as file:
            file.write(test_template.format(name_agent_for_test=name_agent_for_test))

        with open("product_test/list_of_agents.py", "a", encoding="utf-8") as file:
            file.write(f"{name_agent_for_test} = {agent_id}\n")