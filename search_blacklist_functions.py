import requests

router_ip = '192.168.1.1'
user = 'useradmin'
pwd = '3wgzu'

session = requests.Session()
session.verify = False
requests.packages.urllib3.disable_warnings()

login_data = {'username': user, 'psd': pwd}
response = session.post(f'http://{router_ip}/cgi-bin/luci', data=login_data)

resp = session.get(f'http://{router_ip}/luci-static/resources/js/main.js')

content = resp.text

if 'set_host_black' in content:
    print('=== Found set_host_black function ===')
    start_idx = content.find('function set_host_black')
    end_idx = content.find('function ', start_idx + 20)
    print(content[start_idx:end_idx])
    print()

if 'removeBlack' in content:
    print('=== Found removeBlack function ===')
    start_idx = content.find('function removeBlack')
    end_idx = content.find('function ', start_idx + 20)
    print(content[start_idx:end_idx])
    print()

if 'blacklist' in content.lower():
    print('=== Found blacklist related code ===')
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'black' in line.lower():
            print(f'{i+1}: {line}')
