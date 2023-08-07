import requests
from requests.auth import HTTPBasicAuth
import os
import pprint
from dotenv import load_dotenv
import yaml
import json


XTEXT = ["review", "test", "+", "-", "..."]

load_dotenv()
# print(os.getenv('USER-NAME'))

# pprint.pprint(os.getenv('USERNAME'))

# response = requests.get(
#     "https://prunesearch.com/manage?action=yaml&agent_id=19734",
#     verify=False,
#     auth=HTTPBasicAuth(
#         username=os.getenv("USER-NAME"),
#         password=os.getenv("PASS")
#     ))

# content = yaml.load_all(response.content, Loader=yaml.FullLoader)#.decode('utf-8'))
# os.system('curl "https://prunesearch.com/manage?action=yaml&agent_id=19734" -k -u "georgesavr6@gmail.com:YUbhduJuids33" > emit.yaml')
file = open('emit.yaml', 'r', encoding='utf-8')

# con = []
content = yaml.load_all(file, Loader=yaml.FullLoader)
# for data in content:
#     con += data

# fd = open('emit.json', 'w', encoding='utf-8')

# json.dump(con, fd, indent=4)
        # for data in content:
        #     pprint.pprint(data)
        #     break
# print(content[1]['product'])
products = []
i = 1
for data in content:
    product = data[0].get('product', {}).get('properties')
    review = data[0].get('review', {}).get('properties')
    temp_prod = None
    temp_rev = None
    if product:
        for item in product:
            for xtext in XTEXT:
                if xtext in item.get('value').lower():
                    temp_prod = product

            if not item.get('value'):
                temp_prod = product
    if temp_prod:
        products.append(temp_prod)

    if review:
        for item in review:
            children = item.get("children")
            if children:
                for child in children:
                    for xtext in XTEXT:
                        if xtext in item.get('value').lower():
                            temp_rev = review
                    if not item.get('value'):
                        temp_rev = review

            if not item.get('value'):
                temp_rev = review
    if temp_rev:
        products.append(temp_rev)

    # if i == 2:
    #     break
    # i += 1
# pprint.pprint(product)

products_file = open("products.json", "w", encoding="utf-8")
json.dump(products, products_file, indent=2)
products_file.close()
file.close()
