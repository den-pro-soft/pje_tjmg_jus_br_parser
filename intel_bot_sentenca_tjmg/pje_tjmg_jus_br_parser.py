# -*- coding: UTF-8 -*-
import sys

# reload(sys)
# sys.setdefaultencoding('utf8')
import re
import time
import logging
import urllib3
import unicodedata
import pdfkit
import requests

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


LOGIN_URL = 'https://pje.tjmg.jus.br/pje/login.seam'
SEARCH_PAGE = 'https://pje.tjmg.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoavulsa.seam'

logging.basicConfig(
    filename='errors.log',
    filemode='w+',
    format='%(name)s - %(levelname)s - %(message)s'
)

urllib3.disable_warnings()

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
}


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
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(30)
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

    def parse_to_json(self, data):
        filter_dict = {}

        try:
            request_data = re.search(
                                "'parameters':(.*?) } \)", 
                                data) \
                             .group(1) \
                             .split(',')
            
            for item in request_data:
                filter_dict[re.search("'(.*?)'", item).group(1)] = re.search("':(.*?)$", item) \
                                                                     .group(1) \
                                                                     .replace("'", "") \
                                                                     .replace('}', '')
        except:
            pass
        return filter_dict

    def parse(self, number, search_words):
        self.driver.get(LOGIN_URL)
        time.sleep(5)
        self.driver.delete_all_cookies()
        self.driver.add_cookie({
            'name': self.session.cookies.keys()[0], 
            'value': self.session.cookies.values()[0]
        })
        self.get_search_page()
        try:
            search_page = self.session.get(SEARCH_PAGE, headers=headers, verify=False)

        except Exception:
            raise Exception('Connection aborted. Line: 125.')

        soup = BeautifulSoup(search_page.content, 'html.parser')
        view_state = soup.find(id='javax.faces.ViewState')

        get_data = soup.find(id='fPP:searchProcessosPeticao')
        filter_dict = self.parse_to_json(get_data['onclick'])
        number_list = []

        number_list.append(number.split('-')[0])
        number_list += number.split('-')[1].split('.')

        data = {
            'AJAXREQUEST': '_viewRoot',
            'fPP:numeroProcesso:numeroSequencial': number_list[0],
            'fPP:numeroProcesso:numeroDigitoVerificador': number_list[1],
            'fPP:numeroProcesso:Ano': number_list[2],
            'fPP:numeroProcesso:labelJusticaFederal': number_list[3],
            'fPP:numeroProcesso:labelTribunalRespectivo': number_list[4],
            'fPP:numeroProcesso:NumeroOrgaoJustica': number_list[5],
            'fPP': 'fPP', 
            'autoScroll': '',
            'fPP:searchProcessosPeticao': 'fPP:searchProcessosPeticao',
            'javax.faces.ViewState': view_state.get('value'), 
            'AJAX:EVENTS_COUNT': 1
        }
        data.update(filter_dict)

        try:
            response_search = self.session.post(SEARCH_PAGE, data=data, headers=headers, verify=False)
        except Exception:
            raise Exception('Connection aborted. Line: 171.')

        soup = BeautifulSoup(response_search.content, 'html.parser')
        view_state = soup.find(id='javax.faces.ViewState')

        try:
            get_table_search_number = soup.find(id='fPP:processosTable:tb')

        except Exception:
            raise Exception('Search number was not found. Line: 178.')

        try:
            second_a_content = get_table_search_number \
                                .find_all('tr')[0] \
                                .find_all('a')[1]['onclick']
        except Exception:
            raise Exception('Search number was not found. Line: 183.')


        filter_dict = self.parse_to_json(second_a_content)
        filter_dict['javax.faces.ViewState'] = view_state.get('value')

        data.update(filter_dict)

        try:
            response_click = self.session.post(SEARCH_PAGE, data=data, headers=headers, verify=False)
        except Exception:
            raise Exception('Connection aborted. Line: 171.')

        soup = BeautifulSoup(response_click.content, 'html.parser')

        first_string = re.search('var link=(.*?);', soup.text.strip()) \
                         .group(1) \
                         .strip() \
                         .replace('"', '') \
                         .replace(' ', '') \
                         .replace('+', '')
        second_string = re.search('link \+= (.*?);', soup.text.strip()) \
                          .group(1) \
                          .replace('"', '')
        peticionar_url = first_string + second_string

        try:
            response_peticionar = self.session.get(peticionar_url)
        except Exception:
            raise Exception('Connection aborted. Line: 241.')

        soup = BeautifulSoup(response_peticionar.content, 'html.parser')
        view_state = soup.find(id='javax.faces.ViewState')

        try:
            select_cb = soup.find(id='cbTDDecoration:cbTD')['onchange']

        except Exception:
            raise Exception('Search number was not found. Line: 249.')

        filter_dict = self.parse_to_json(select_cb)

        filter_dict['AJAXREQUEST'] = data['AJAXREQUEST']
        filter_dict['ipDescDecoration:ipDesc'] = 'Petição'
        filter_dict['javax.faces.ViewState'] = view_state['value']
        filter_dict['cbTDDecoration:cbTD'] = 13
        filter_dict['AJAX:EVENTS_COUNT'] = 1
        filter_dict['ipNroDecoration:ipNro'] = ''
        filter_dict['docPrincipalEditorTextArea'] = '<p>peticao area</p>'
        filter_dict['context'] = '/pje'
        filter_dict['mimes'] = 'application/pdf'
        filter_dict['mimesEhSizes'] = 'application/pdf:3.0'
        filter_dict['modalConfirmaLimparOpenedState'] = ''
        filter_dict['modalErrosOpenedState'] = ''
        filter_dict['quantidadeProcessoDocumento'] = 0

        try:
            save_peticao = self.session.post(
                peticionar_url, 
                data = filter_dict, 
                headers = headers, 
                verify = False)
        except Exception:
            raise Exception('Connection aborted. Line: 256.')

        soup = BeautifulSoup(save_peticao.content, 'html.parser')
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
    b.parse('5101476-91.2017.8.13.0024', search_words)
    b.driver.quit()
