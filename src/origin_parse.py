from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

site = "https://www.pcgamingwiki.com/wiki/List_of_Origin_Access_games"
hdr = {'User-Agent': 'Mozilla/5.0'}
req = Request(site, headers=hdr)
page = urlopen(req)
soup = BeautifulSoup(page, 'html.parser')


def table_extract(item):
    table = item.find_all('th', {'class': 'table-origin-body-game'})
    out = [i.text for i in table]
    return out


def origin_games():
    table_list = soup.find_all('div', {'class': 'container-pcgwikitable'})
    final = [table_extract(item) for item in table_list]
    basic = final[1]
    basic_out = [[item, 'Basic'] for item in basic]
    premiere = final[0]
    premiere_out = [[item, 'Premiere'] for item in premiere]
    return basic_out, premiere_out


origin_games()
