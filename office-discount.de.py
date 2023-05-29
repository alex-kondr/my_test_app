from random import randint

from agent import *
from models.products import *



OPTIONS = "-H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=YstLhqBXR16BypODDBiKNIxDdGQAAAAAQUIPAAAAAAB1QxfwulJVKWK3j7xg8Spc; incap_ses_1572_2623194=p299Np618U7L1wyo/93QFf1fdGQAAAAAzIuY20onjF99waOr5Lsf1w==; nlbi_2623194=aQCKT1r9+jSP7y+kiGaaigAAAADoEYPIIBNb0K8GDdm7LaMN; nlbi_2623194_2147483392=R9nFLIUqOE+PaVrZiGaaigAAAADE+/0wRW+sX7CspJKB3roX; reese84=3:KWV3J69UQsEf4RYbzI25lA==:+a0FWiudyoYnEkroJE5wsgXmz5pKfU0cAA6Ye7129L8K2sp15y89eF7NqLZ41teCC2Hg1N+2K0bDvP26qUzUES2diM79LxkDg2Az+N8z2Z+VIMSztR5lcPCpPHnCrrlAZl70dGfIaDrrh2NwnlugGhdneTJJtHB8TpS+vZmerg+I9qoXU+bwOhUTPLGXIX5QhoOWBCNKavEdmcNsEDUQbYZFI8y64aOkKkcQJtkX+DEfA62cb0NUiKvZOb5Qeqxs7qwIgp6BdJXnt5lPtF/x9yaLuPx69vN70Lnj4QBYg0w0jYXwAjfF39nUswdYerhBLhZpbeHGtiEosPCwoIBlc+kOhBXWkrQaX9rE1gaQL8CNYgAzRUo/ZMR9AkPYh8qkPdMxuK0ArQFzlXKBw2L9p5L3ovYHwdkQMYU2Dmjsvloi/56+PhkDRPNj6I6e0naV2PGlflwgPuhDIB2uYGY33A==:aKzF1JNurEpt7F0tpV/GqyVAhiPU+leeQYeZPtcxW+Q=; SSLB=1; SSID=CQDgdR04AAAAAACOQ3RkyhhAAI5DdGQBAAAAAAA6eFVmjkN0ZADJiuoCAAOtcgAAjkN0ZAEA7AIAAehyAACOQ3RkAQDtAgABEHMAAI5DdGQBAIQCAAH2XAAAjkN0ZAEA; SSRT=1mJ0ZAADAA; WC_GENERIC_ACTIVITYDATA=[6116084569%3Atrue%3Afalse%3A0%3AkpNSZ4rWE1HTCLd6%2BOOzWXcQ4uhRkuPMdFtx8hpz3AU%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685341070495-809952][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; ecToken=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJXQyIsImV4cCI6MTY4NTM1MDI3OCwianRpIjoiZlRZcXlQT09mLXpiVk45Q1FGckJIZyIsImlhdCI6MTY4NTM0OTA3OCwic3ViIjoidXNlcl9qd3QiLCJzaG9wQ3VzdG9tZXJOdW1iZXIiOiItMTAwMiIsInJlZ2lzdHJhdGlvblR5cGUiOiIiLCJzYXBDdXN0b21lck51bWJlciI6bnVsbCwic3RvcmVJZCI6IjEwMDA2IiwiYXVkIjoic2VydmljZXMifQ.cYjxR0zt-ab4bsvFB_l26tODyKx2b0hbWHQaXTq4FPUqIhAFaVjX_6Iheg1Q7tYSfu-IsJcNJ2OdPKgLayCKA3XFtIVj066DoFsdGuvXNLPX6b9iSC__JtTIFJHZJqKSRfzR-wuKXP9hn84lbp83W0oFz91EGmMj2bNi8DLtHbccn4bjgYP8znwEuAhSCz8fz5ozX7n6AscwuBY6wvnX4E7IcycMnGoa0_9G9ZvhjUD1JCH-C5xvShxXsmU3e_fmGb_4i5knR_-7KdgtQsGqOoOJggRZhJfIISOlN0IrA2zp8bJ5ObaeGPA-ECizaXXo75s76Ms3YqH526m3Tti3QA; WC_PERSISTENT=MKOjGnXLUev8jdv43S9eS0%2BrqAfw%2Fx5dH48vfo58OC8%3D%3B2023-05-29+08%3A17%3A50.5_1685341070495-809952_10006_-1002%2C-3%2CEUR_10006; WC_ACTIVEPOINTER=-3%2C10006; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; uvid=493714b8-afe8-402c-8725-7c98f56a0bae; JSESSIONID=0000z_GUy7xFJ1wS0Ts3IT4LORJ:1bj7vt3bc; WC_SESSION_ESTABLISHED=true; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1362788575%2C6GTMdu3mv98ClCGl9jOCOmMlq7FOxiErTSN%2BlrSdCdaBvbPfsfEVnNFZe4aX5iH%2BM%2B9N8aKVEeeJcFu89F3uE4K%2FlddkZlXrBg1wV%2FSE9CPlpjyU4pQysz3%2FcO6ICTxAVd%2F9759EoY4BZiWfDfagltIvcpXXfnL05gb3Y9TZBULO4lt4pa3oj5rFlARnhIpw1%2BHzAo%2B%2FK2Ex9FVWmnW4jqK8uuvpQWFQoUFZVrSl102XP0xos0UQxO0meFi3EPf7; SSSC=22.G7238484778259847370.1|644.23798.0:746.29357.1:748.29416.0:749.29456.0; _ga_7GM3G61HNK=GS1.1.1685341079.1.1.1685349101.37.0.0; _ga=GA1.1.1922368939.1685341080; _gid=GA1.2.1159212601.1685341081; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=da7bd26abcc06d9131be2519375ed87e|0529344197c65db64931ece72cd8c2bc4a02140f.4513333998.1685344657695$052908123f9e89f482cc3d52712ccbc0794bc7e5.1037162625.1685344689488$05295174113a340370d405085837985f21c1feff.1037162625.1685345814257$05295527eee2e773c65239bbcf2cb7a18ba2b923.47.1685347078144$052941327a1871498b78f1e63dedcbc9de6f316d.4513333998.1685349057955$05291986ac4daae83f14c4ab200855ee6407b195.47.1685349084441|1685350132918||16|||0|17.88|3.85882; _fbp=fb.1.1685341081721.1168505427; cto_bundle=XuGk2F90TVAlMkJvRGVFbVp2NXJtU09xeUNxdCUyRmZpbkolMkJCYWxlNHFKV3owUjFzc2QxNHg2SmxsaFVUJTJGQjQlMkY3Q2luSzFBVUd1dkw4RkclMkZreHNGSTk0dWZNZzVPWU0yTkNDNHFzcWw4alFjT0h5JTJGS1QlMkZSNzVnYjloUmdmYW44ZWZIcjdkbTk4cEpPNEk3MHhvalRvNnU5c2lRbG9BJTNEJTNE; mf_user=8c0d46e87e7bfce20c7f721d83975fe1|; 3a3276486f1fdb89f1eb46f1a28ff467=83bb121dcd854fbf301b13391285e969; incap_ses_1084_2623194=Aj43QTDPfwaui4PlMyULD1ZXdGQAAAAAYrcn3Vr311N/QwGL9N6JTA==; skz=1086274' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1'"


def run(context, session):
    session.queue(Request('https://www.office-discount.de/papier/additions-fax-kassenrollen', use='curl', options=OPTIONS, max_age=0), process_category, dict())


def process_frontpage(data, context, session):    
    cats1 = data.xpath("//div/ul/li[@id]")
    for cat1 in cats1:
        name = cat1.xpath("a//text()").string().encode("utf-8")
        print("name1=", name)
        # cats2 = cat1.xpath("ul/li")
        # for cat2 in cats2:
        #     name2 = cat2.xpath("a//text()").string()
        #     cats3 = cat2.xpath("ul/li/a")
        #     for cat3 in cats3:
        #         name3 = cat3.xpath(".//text()").string()
        url = cat1.xpath("a/@href").string().encode("utf-8")
        print("url_process_frontpage=", url)
        session.queue(Request(url, use="curl", options=OPTIONS, max_age=0), process_category1, dict(context=context, name=name))


def process_category1(data, context, session):
    print("data_process_category1=", data.raw)
    cats = data.xpath("//div/ul/li[@class='']")
    # print("cats=", cats.pretty())
    for i, cat in enumerate(cats):
        url = cat.xpath("a/@href").string().encode("utf-8")
        print(i, ": url_process_category1=", url)
        name = cat.xpath("a//text()").string().encode("utf-8")
        print("name=", name)
        session.queue(Request(url, use="curl", options=OPTIONS, max_age=0), process_category2, dict(context=context, name=name))


def process_category2(data, context, session):
    print("data_process_category2=", data.raw)
    cats = data.xpath("/")
    print("cats_process_category2=", cats.pretty())
    # for cat in cats:
    #     url = cat.xpath("li[@class=""]/a/@href").string()
    #     name = cat.xpath("li[@class=""]/a//text()").string()
    #     session.queue(Request(url), process_product2, dict(context, url=url, name=name))
    

def process_category(data, context, session):
    prods = data.xpath('//div[@class="article-content"]/div/strong/a')
    print("prods=", prods.pretty())
    for prod in prods:
        url = prod.xpath("@href").string()
        name = prod.xpath("span//text()").string()
        session.queue(Request(url), process_product, dict(context, url=url, name=name))
        

def process_product(data, context, session):
    product = Product()
    product.name = context['name']
    print("name_process_product=", context['name'])
    product.url = context['url']
    print("url_process_product=", context['url'])
