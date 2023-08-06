import requests
from requests.auth import HTTPBasicAuth
import os
import pprint
from dotenv import load_dotenv
import yaml

load_dotenv()

# pprint.pprint(os.getenv('USERNAME'))

response = requests.get(
    "https://prunesearch.com/manage?action=yaml&agent_id=19734",
    verify=False,
    auth=HTTPBasicAuth(
        username=os.getenv("USERNAME"),
        password=os.getenv("PASS")
    ))

content = yaml.load_all(response.content, Loader=yaml.FullLoader)#.decode('utf-8'))
# content = os.system('curl "https://prunesearch.com/manage?action=yaml&agent_id=19734" -k -u "georgesavr6@gmail.com:YUbhduJuids33" > emit.yaml')
# print(content[1]['product'])
i = 1
for data in content:
    pprint.pprint(data[0].get('product', {}).get('properties', [{}])[0].get('value'))
    if i == 2:
        break
    i += 1