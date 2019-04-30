# -*- coding: UTF-8 -*-
import sys

# reload(sys)
# sys.setdefaultencoding('utf8')

import time
import logging
import unicodedata

from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pdfkit
import requests


LOGIN_URL = 'https://pje.tjmg.jus.br/pje/login.seam'
SEARCH_PAGE = 'https://pje.tjmg.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam'

logging.basicConfig(
    filename='errors.log',
    filemode='w+',
    format='%(name)s - %(levelname)s - %(message)s'
)


class Bot(object):
    def __init__(
            self,
            digital_user,
            digital_password,
            digital_api_url='http://rpa-ui-windows-test.intelligenti.com.br/',
            headless=False
    ):
        self.headless = headless
        self.authentication_type = 'session_key'
        self.session_name_key = 'JSESSIONID'
        self.session_key = 'bjk6Frc5jiUcGVuFNk2NhnuMU5rEINZOqzg6D8xq.pje2ext-5'
        self.digital_api_url = digital_api_url
        self.digital_user = digital_user
        self.digital_password = digital_password
        self.driver = self.setup_driver()
        self.session = self._login()

    def setup_driver(self):
        options = webdriver.FirefoxOptions()

        if self.headless:
            options.add_argument('-headless')

        driver = webdriver.Firefox(
            service_log_path='/dev/null',
            options=options,
            executable_path='geckodriver'
        )
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(15)
        driver.set_window_size(1360, 900)

        return driver

    def is_visible_element(self, by_type, locator, timeout=20):
        try:
            if by_type == "name":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((By.NAME, locator)))
            elif by_type == "selector":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, locator)))
            elif by_type == "xpath":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((By.XPATH, locator)))
            elif by_type == "class":
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, locator)))
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((By.ID, locator)))
            return True
        except Exception:
            return False

    def _login(self):
        session_bot = requests.Session()

        if self.authentication_type == 'session':
            session_bot.cookies.set(self.session_name_key, self.session_key)

        else:
            login_admin_url = 'admin/login/?next=/admin/'
            # response = requests.get('http://127.0.0.1:8000/digital_api/get_pje_cookie/?url=https://pje.tjdft.jus.br/pje/login.seam')
            session = requests.session()
            session.get(self.digital_api_url + login_admin_url)
            token = session.cookies['csrftoken']
            login_data = dict(
                username=self.digital_user,
                password=self.digital_password,
                csrfmiddlewaretoken=token
            )

            session.post(self.digital_api_url + login_admin_url, data=login_data)

            response_cookies = session.get(
                self.digital_api_url + 'digital_api/get_pje_cookie/?url={}'.format(
                    LOGIN_URL)).json()

            if isinstance(response_cookies, dict):
                if response_cookies.get('status', '') == 'fail':
                    raise Exception('Login to website failed. Please check API server.')

            session_bot.cookies.set(response_cookies[0]['name'], response_cookies[0]['value'])

        return session_bot 

    def get_search_page(self):
        self.driver.get(SEARCH_PAGE)

    def switch_to_window(self, window_id):
        self.driver.switch_to.window(self.driver.window_handles[window_id])

    def parse(self, number, search_words):
        import pdb;
        pdb.set_trace()
        self.driver.get(LOGIN_URL)
        time.slee(3)
        self.driver.delete_all_cookies()
        self.driver.add_cookie({
            'name': self.session.cookies.keys()[0], 
            'value': self.session.cookies.values()[0]
        })
        self.get_search_page()
        try:
            if SEARCH_PAGE != self.driver.current_url:
                logging.warning('Error login. Please check your session.')
                return None

        except Exception:
            logging.warning('Error login. Please check your session.')
            return None

        #Not implemented yet....

    def generate_pdf(self, content):
        html = '''
            <!DOCTYPE HTML>
            <html>
                <head>
                    <meta charset="utf-8">
                </head>
                <body>
                    {content}
                </body>
            </html>
            '''.format(content=content)

        options = {
            'quiet': ''
        }

        pdf = HeadlessPdfKit(html, 'string', options=options).to_pdf(False)

        return pdf


class HeadlessPdfKit(pdfkit.PDFKit):
    def command(self, path=None):
        cmdlist = ['xvfb-run', '--']
        # if `auto_servernum` is in options, add the `-a` parameter which
        # should ensure that each xvfb has its own DISPLAY ID
        if 'auto_servernum' in self.options:
            cmdlist = ['xvfb-run', '-a', '--']
        return cmdlist + super(HeadlessPdfKit, self).command(path)


if __name__ == '__main__':
    b = Bot(digital_user='admin', digital_password='123098skd123!98S_')
    search_words = [u"Sentença"]
    b.parse('1000665-82.2016.5.02.0381', search_words)
    b.parse('0010059-02.2015.5.01.0541', search_words)
    b.driver.quit()
