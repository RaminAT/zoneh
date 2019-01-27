"""
Zone-H cybercrime archive grabber for investigation purpose with country and
hostname(TBD) filtering.
"""

import logging
import sys
import time
import random
import requests
from bs4 import BeautifulSoup

from zoneh.iso3166 import COUNTRY_DICT

HOST = 'www.zone-h.org'
BASE_URL = f'https://{HOST}'
MIRROR_URL = f'{BASE_URL}/mirror/{{mirror_id}}'

ARCHIVE_URL = f'{BASE_URL}/archive'
ARCHIVE_PAGE_URL = f'{ARCHIVE_URL}/page={{page_num}}'
ARCHIVE_SPECIAL_URL = f'{ARCHIVE_URL}/special=1'
ONHOLD_URL = f'{ARCHIVE_URL}/published=0/page={{page_num}}'

TBL_ID = 'ldeface'
TBL_SKIP_ROWS = (1, -2)
TBL_PAGE_NUMS_ROW_ID = -2
TBL_COUNTRY_TD_IDX = 5
TBL_SPECIAL_TD_IDX = 6
TBL_MIRROR_TD_IDX = 9
START_PAGE = 1

"""
Cookies are generated by JS, currently need to be manually set. Can be 
improved by getting them by using Selenium Webdriver or pyppeteer.

Example 'COOKIES_STR' string:
'PHPSESSID=gj7b52fn1tcgh34jnkj43kj; ZHE=34kl5jkl5j3klj534gn3ngkln3qkjb4g'
"""
# TODO: move to config file?
COOKIES_STR = ''

HEADERS = {'Host': HOST,
           'Connection': 'keep-alive',
           'Cache-Control': 'max-age=0',
           'Upgrade-Insecure-Requests': '1',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
           'Referer': 'http://www.zone-h.org/login?hz=1',
           'Accept-Encoding': 'gzip, deflate',
           'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8,uk;q=0.7',
           'Cookie': COOKIES_STR}


"""
Lowering the values increases the risk of getting perm banned by Zone-H's
anti-DDoS logic.
"""
SLEEP_TIME = lambda: random.randint(4, 7)


class ZoneHError(Exception):
    """Base ZoneH exception."""
    pass


class ZoneH:
    """TODO"""
    def __init__(self):
        """Class consrtuctor."""
        self._log = logging.getLogger(__name__)
        self._session = requests.session()
        self._session.headers.update(HEADERS)
        try:
            cookies = [requests.cookies.create_cookie(*cook.split('=')) for
                       cook in COOKIES_STR.split(';')]
        except TypeError:
            err_msg = 'Empty \'COOKIES\' string?'
            self._log.error(err_msg)
            sys.exit(err_msg)
        for cookie in cookies:
            self._session.cookies.set_cookie(cookie)

    def get_archive(self, page_num=None, single=None, country=None):
        """TODO"""
        return self.__get_archive(page_num=page_num, single=single,
                                  country=country)

    def get_archive_special(self, page_num=None, country=None, single=None):
        """TODO"""
        return self.__get_archive(special=True, page_num=page_num,
                                  single=single,
                                  country=country)

    def get_onhold(self, page_num=None, single=None, country=None, start=None,
                   end=None):
        """TODO"""
        return self.__get_archive(onhold=True, single=single,
                                  page_num=page_num,
                                  country=country, start=start, end=end)

    def __get_archive(self, page_num=None, single=None, special=False,
                      onhold=False, country=None, start=None, end=None):
        """TODO"""
        data = {}
        country = COUNTRY_DICT.get(country)

        if special:
            url = ARCHIVE_SPECIAL_URL
        elif onhold:
            url = ONHOLD_URL
        else:
            url = ARCHIVE_URL
        try:
            if start or end:
                start = start or START_PAGE
                end = end or self._get_pages_count()
                if start > end:
                    raise ZoneHError('Start page can\'t be larger than End page')
                data = self.__get_pages(start, end, url, country)
            elif single:
                self._log.info(f'Processing single page: {page_num}')
                archive = self._make_request(url=url)
                data[page_num] = self._process_soup(archive, country=country)
            else:
                num_of_pages = self._get_pages_count()
                self._log.info(f'Getting whole archive, number of pages: '
                               f'{num_of_pages}')
                start, end = START_PAGE, num_of_pages + 1
                data = self.__get_pages(start, end, url, country)
        except ZoneHError as err:
            sys.exit(str(err))
        return data

    # TODO: Retry decorator
    def _make_request(self, url):
        """TODO"""
        try:
            self._log.debug(f'URL: {url}')
            res = self._session.get(url=url)
            self._verify_result(res)
        except Exception as err:
            # TODO
            err_msg = 'Issue with request to Zone-H'
            self._log.exception(err_msg)
            raise ZoneHError(err_msg) from err
        return res

    def _verify_result(self, result):
        """TODO"""
        # TODO
        return result

    def _process_soup(self, page, country=None):
        """TODO"""
        data = []
        try:
            soup = BeautifulSoup(page.content, 'html.parser')
            table = soup.find('table', attrs={'id': TBL_ID})
            rows = table.find_all('tr')
            start_slice, end_slice = TBL_SKIP_ROWS

            for row in rows[start_slice:end_slice]:
                cols = row.find_all('td')
                cols_data = []

                for index, col in enumerate(cols):
                    if index == TBL_COUNTRY_TD_IDX:
                        col = col.find('img').get('title') if col.find(
                            'img') else ''
                        if country and col != country:
                            cols_data = []
                            break

                    elif index == TBL_MIRROR_TD_IDX:
                        col = int(col.find('a').get('href').rsplit('/', 1)[1])
                    elif index == TBL_SPECIAL_TD_IDX:
                        col = bool(col.find('img'))
                    else:
                        col = col.text.strip()
                    cols_data.append(col)

                if cols_data:
                    data.append(cols_data)
        except Exception as err:
            err_msg = 'Can\'t process fetched HTML page'
            self._log.exception(err_msg)
            raise ZoneHError(err_msg)
        return data

    def _get_pages_count(self):
        """TODO"""
        try:
            first_page = self._make_request(
                ARCHIVE_PAGE_URL.format(page_num=START_PAGE))
            soup = BeautifulSoup(first_page.content, 'html.parser')
            table = soup.find('table', attrs={'id': TBL_ID})
            row = table.find_all('tr')[TBL_PAGE_NUMS_ROW_ID]
            col = row.find('td')
            pages_count = int(col.find_all('a')[-1].text)
        except AttributeError as err:
            if soup.find('img', attrs={'id': 'cryptogram'}):
                err_msg = 'Captcha request, solve in the browser before ' \
                          'trying again'
                self._log.exception(err_msg)
                raise ZoneHError(err_msg) from err
            else:
                err_msg = 'Couldn\'t find HTML element. Check logs'
                self._log.exception(err_msg)
                raise ZoneHError(err_msg) from err
        except ZoneHError:
            raise
        except Exception as err:
            err_msg = 'Unknown error during getting page count. Check logs'
            self._log.exception(err_msg)
            raise ZoneHError(err_msg) from err
        return pages_count

    def __get_pages(self, start, end, url, country):
        """TODO"""
        data = {}
        for num in range(start, end + 1):
            self._log.info(f'Processing page: {num}')
            res = self._make_request(url=url.format(page_num=num))
            data[num] = self._process_soup(res, country)
            self._log.debug(data[num])
            time.sleep(SLEEP_TIME())
        return data