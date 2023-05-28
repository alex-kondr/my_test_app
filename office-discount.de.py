from agent import *
from models.products import *


# 234 -> 1900
# 4853 -> 6000
# 7123 -> 9000
# 9486 -> 10000


OPTIONS = "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3' -H 'Accept-Encoding: deflate' -H 'Referer: https://www.office-discount.de/papier/additions-fax-kassenrollen' -H 'Connection: keep-alive' -H 'Cookie: visid_incap_2623194=vZCqGZcHSeORCSb8xgWkvhtOcmQAAAAAQUIPAAAAAAAUHg/Wn3j7BnFcb9s/GpyL; reese84=3:7XwQdAAht8Ege2d1zE5Fzg==:eFr3oQ3/32/jME7HIQ2alZsjeUFYsCHUImV/6waV2ri/hU8eqcLkX5bG6zX/izFmLVhHTUOKBzQiRRJQIpz0Yj+e/zNzrZMJ5cF17sUDxgD2hO4eZ/NvHwF7lxuqJ1HA3vxBP8h2eRSs11DXBrdquqeR5BpJrf5xex7TiGmN0ssuLbhWRzEbR/B2oyN6X+sbI2dyzLB2rekYOOL6+qOYgRXyEkAJ4tCt2z1G4EjERicpMe+mrlRZEvcNavN9HSeZNG6voUkbFsGcGPPPNKpyD6xrCmu6qQb+MwXJYApSnQkkUONCRnebzJTkL/jsz4tYC6eJP0tSvmvY45mQn02KeftShTJUFtzrviKSWDZAjXP1I6i1t35BTK+EM468obGHQbi0q6wsMfySvatlpBLHATvOof8vJW/MDQVR04uD/tmOmRLM7HaUmxm8hMmk/65osFSg3qXvNhB8W9XjGVP/Dw==:hnlZoVWydDXPqsj4Ds+wvXRnNEVD6hIc0HKyMXawCzo=; SSLB=1; SSID=CQBVhB04AAAAAAAfTnJkcF1AAB9OcmQDAAAAAADP2VRmI6VzZADJiuoCAAOtcgAAH05yZAMA7AIAA-hyAAAfTnJkAwCEAgAB9lwAACOlc2QBAO0CAAMQcwAAI6VzZAEA; SSRT=NbJzZAADAA; uvid=02b664cc-d53d-4eb8-b09d-88fe2e66b261; WC_PERSISTENT=Yih5AptDkfs6AresKTYDqWm2871SWdwn8jP2%2Fe1Ui5w%3D%3B2023-05-27+20%3A38%3A23.051_1685212703043-520431_10006_-1002%2C-3%2CEUR_10006; _ga_7GM3G61HNK=GS1.1.1685300514.3.1.1685303884.38.0.0; _ga=GA1.1.997405017.1685212719; _gid=GA1.2.938923987.1685212719; _fbp=fb.1.1685212722852.1529141951; cto_bundle=Tyt57l9WV1JqNDd2TnFjaGxMQlVHNGh2MlRPQXNCekpyZ1lJJTJGRHRwbmlpJTJCM3d4TWJCaUxwQXloTUJ5Nk5weG9FcHZXVks3eE1VRDh0Q1ZVdCUyRnBzRGFnN1dTRFlpayUyQmU1QnBPTXRKUFd5ZDlQRHFyT2w1UGxya1clMkIwS25PbXVrVVY2SkJueE5mRzZ5aFVKNXI4TE5GMG9LVkVBJTNEJTNE; incap_ses_689_2623194=KQIaXc6DpDR/zFP0zdKPCUafc2QAAAAAK0n0xdr/hb4bx7dtjqZzZA==; nlbi_2623194_2147483392=9R7fCMtQhWKHFXsCiGaaigAAAADGF6n9yJbfbz9OFJNcooAk; WC_GENERIC_ACTIVITYDATA=[6114542480%3Atrue%3Afalse%3A0%3Acm6QtrsEBzO3WTvqdXVVHT9ddZsZHr2O5V7sZilPbrE%3D][com.ibm.commerce.context.entitlement.EntitlementContext|10508%2610508%26null%26-2000%26null%26null%26null][com.ibm.commerce.context.audit.AuditContext|1685212703043-520431][com.ibm.commerce.context.globalization.GlobalizationContext|-3%26EUR%26-3%26EUR][com.ibm.commerce.catalog.businesscontext.CatalogContext|66556%26null%26false%26false%26false][de.printus.ecs.offerprice.businesslogic.commands.UgsSpecialReducedPriceContext|null][CTXSETNAME|Store][com.ibm.commerce.context.base.BaseContext|10006%26-1002%26-1002%26-1][com.ibm.commerce.giftcenter.context.GiftCenterContext|null%26null%26null]; WC_SESSION_ESTABLISHED=true; WC_USERACTIVITY_-1002=-1002%2C10006%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C1498267454%2CXlPEY6UgAIb2TuHK%2BSIduCAVLPP1vE5k0mVQqpANlRenXQrdweulTF96PxauQrGKi7nN%2BfsbA5cKxgvRatx0NdhH1KWslkxEITQyIWVSXVayb9RlnusWEIDQeXT9G9UPGTIAA8hCvCjoo9G949NpD73diC1JryU0rGKeiE86G8FpX5nNddkd4eJ0WIG0SZ1ca6IXlJ%2FOi%2Bu8sRiofAwXZcuxbOefkEC4wCsxk11XEghNVzSPDn1fQK7cjrGZv7QV; JSESSIONID=0000QH2GOWnQHZOS0RtDS_DtEI1:1bj7vub5m; WC_ACTIVEPOINTER=-3%2C10006; WC_AUTHENTICATION_-1002=-1002%2Co8%2FX4CGzdvUkhmGvFf4RJRbEQwMNU15y9%2Fz%2BaQaaNXs%3D; nlbi_2623194=eOjpVSfYuS+snAC8iGaaigAAAADprqRpPUElZMF9k8ILEjBb; SSSC=22.G7237933446192979312.3|644.23798.0:746.29357.1:748.29416.1:749.29456.1; mf_c4116c55-2185-4b8e-9bdb-b24b5ea1eda9=6480130cc1e90df918b80e599ad19ed3|05282096f61a83d993d41900cdc59b99facb87ff.47.1685302697892$05284872c35ca3be113cffdb25c5b48f02e2d021.-2232480058.1685303053638$05282665e3426199188926fcbc4255a68976700b.47.1685303106707$05281506e282739a593847a06b1de23c888df60b.-2232480058.1685303355956$05280004c79a9cc5d545381ef1a54362fb3a4124.9368726452.1685303589954$05285044c903a4b5a6e28ea8fdf3196a7bbf9ab3.47.1685304271392|1685304271645||9|||0|17.88|2.22549; mf_user=ecf28b6dd5898f3b51805c049b488d06|; 3a3276486f1fdb89f1eb46f1a28ff467=83bb121dcd854fbf301b13391285e969; ecToken=eyJhbGciOiJSUzI1NiJ9.eyJpc3MiOiJXQyIsImV4cCI6MTY4NTMwNTA2MSwianRpIjoiVE5VSVFYNGI3NFZUb2JyaWlBRFdKZyIsImlhdCI6MTY4NTMwMzg2MSwic3ViIjoidXNlcl9qd3QiLCJzaG9wQ3VzdG9tZXJOdW1iZXIiOiItMTAwMiIsInJlZ2lzdHJhdGlvblR5cGUiOiIiLCJzYXBDdXN0b21lck51bWJlciI6bnVsbCwic3RvcmVJZCI6IjEwMDA2IiwiYXVkIjoic2VydmljZXMifQ.a9AyrTk8LrUyve4_h1yxJVgIyAVg_aV5hPbHzLpl1cIyTNd7wc3m_HQGwb-DaHC5dFi7ZSfd9wnfUZckw55NMdpd9aiGS18Ru_nIqNBLg3bouItPSLGztK0TES8sgMBJ4qKB9Kamnf4lpAM9VWNsw6vfmtyx95OhGsvAvS00TCV7derGl5sac3Jwf_9AOVAKr-olWBHih5k4jjZX84E_q91r2mF3vHu2qLqaHzFA720KFs5zf7g1l-OHt3AQEwrVlzf0X7P55mdL0qOpMvhQY3YrGcZ4f7lowIVJaqa5DFgylwYazTE0oHS8-YiXa0jzchPBLvHZrtACsjWV2WA80A; skz=1086274' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-User: ?1' -H 'TE: trailers'"

def run(context, session):
    session.queue(Request('https://www.office-discount.de/', use='curl', options=OPTIONS), process_frontpage, dict())


# category
# product
# reviews
def process_frontpage(data, context, session):
    cats1 = data.xpath("//div/ul")
    for cat1 in cats1:
        name1 = cat1.xpath("li[@id]/a//text()").string()
        print("name1=", name1)
        # cats2 = cat1.xpath("ul/li")
        # for cat2 in cats2:
        #     name2 = cat2.xpath("a//text()").string()
        #     cats3 = cat2.xpath("ul/li/a")
        #     for cat3 in cats3:
        #         name3 = cat3.xpath(".//text()").string()
        url = cat1.xpath("li[@id]/a/@href").string()
        session.queue(Request(url, use="curl", options=OPTIONS), process_category1,
                        dict(cat=name1))


def process_category1(data, context, session):
    cats = data.xpath("//div/ul")
    for cat in cats:
        url = cat.xpath("li[@class=""]/a/@href").string()
        name = cat.xpath("li[@class=""]/a//text()").string()
        print("name=", name)
        session.queue(Request(url, use="curl", options=OPTIONS), process_category2, dict(context, url=url, name=name))


def process_category2(data, context, session):
    print("data=", data.raw)
    # cats = data.xpath("//div/ul")
    # for cat in cats:
    #     url = cat.xpath("li[@class=""]/a/@href").string()
    #     name = cat.xpath("li[@class=""]/a//text()").string()
    #     session.queue(Request(url), process_product2, dict(context, url=url, name=name))

