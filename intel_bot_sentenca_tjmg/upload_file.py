# -*- coding: UTF-8 -*-
import sys
import time

reload(sys)
sys.setdefaultencoding('utf8')
import re
import logging
import urllib3
import pdfkit
import requests
import json
from bs4 import BeautifulSoup

BASE_URL = 'https://pje.tjmg.jus.br'
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
    session_name_key = 'JSESSIONID'

    def __init__(
            self,
            digital_user=None,
            digital_password=None,
            digital_api_url='http://rpa-ui-windows-test.intelligenti.com.br/',
            authentication_type='api',
            session_key=None
    ):
        self.digital_api_url = digital_api_url
        self.digital_user = digital_user
        self.digital_password = digital_password
        self.authentication_type = authentication_type
        self.session_key = session_key

        self.session = self._login()

    def _login(self):
        session_bot = requests.Session()

        if self.authentication_type == 'session':
            session_bot.cookies.set(self.session_name_key, self.session_key)

        else:
            login_admin_url = 'admin/login/?next=/admin/'
            session = requests.session()
            session.get(self.digital_api_url + login_admin_url)
            token = session.cookies['csrftoken']
            login_data = dict(
                username=self.digital_user,
                password=self.digital_password,
                csrfmiddlewaretoken=token
            )

            session.post(self.digital_api_url + login_admin_url,
                         data=login_data)

            self.response_cookies = session.get(
                self.digital_api_url + 'digital_api/get_pje_cookie/?url={}'.format(
                    LOGIN_URL)).json()

            if isinstance(self.response_cookies, dict):
                if self.response_cookies.get('status', '') == 'fail':
                    raise Exception(
                        'Login to website failed. Please check API server. Line 75.')

            session_bot.cookies.set(self.response_cookies[0]['name'],
                                    self.response_cookies[0]['value'])

        return session_bot

    def parse_to_json(self, data):
        filter_dict = {}

        try:
            request_data = re.search(
                "'parameters':(.*?) } \)",
                data) \
                .group(1) \
                .split(',')

            for item in request_data:
                filter_dict[re.search("'(.*?)'", item).group(1)] = re.search(
                    "':(.*?)$", item) \
                    .group(1) \
                    .replace("'", "") \
                    .replace('}', '')
        except:
            pass
        return filter_dict

    def parse(self, number):
        try:
            search_page = self.session.get(SEARCH_PAGE, headers=headers,
                                           verify=False)

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
            response_search = self.session.post(SEARCH_PAGE, data=data,
                                                headers=headers, verify=False)
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
            response_click = self.session.post(SEARCH_PAGE, data=data,
                                               headers=headers, verify=False)
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
            response_peticionar = self.session.get(peticionar_url,
                                                   headers=headers,
                                                   verify=False)
        except Exception:
            raise Exception('Connection aborted. Line: 241.')

        soup = BeautifulSoup(response_peticionar.content, 'html.parser')
        jds = [i for i in soup.find_all('script') if
               'concluirPeticionamento' in str(i)][0]['id']

        view_state = soup.find(id='javax.faces.ViewState')
        cid = soup.find("input", {"name": "cid"})['value']

        containerIds = [i for i in soup.find_all('script') if 'limparTipoProcessoDocumento' in str(i)][0]
        values_id = str(containerIds)[64:].split(',')
        containerId = values_id[3].split(':')[-1].replace("'", '')

        # STEP 1
        headers['Referer'] = peticionar_url
        popup_url = 'https://pje.tjmg.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoPopUp.seam'

        data_step_1 = {
            'AJAXREQUEST': containerId,
            'formularioUpload': 'formularioUpload',
            'cbTDDecoration:cbTD': '13',
            'ipDescDecoration:ipDesc': u'Petição',
            'ipNroDecoration:ipNro': '',
            'docPrincipalEditorTextArea': """"<p>peticao area</p>""",
            'context': '/pje',
            'cid': cid,
            'mimes': 'application/pdf',
            'mimesEhSizes': 'application/pdf:3.0',
            'modalConfirmaLimparOpenedState': '',
            'modalErrosOpenedState': '',
            'quantidadeProcessoDocumento': '0',
            'javax.faces.ViewState': view_state['value'],
            'jsonProcessoDocumento': json.dumps({"array": "[{\"nome\": \"test.pdf\", \"tamanho\": 36421, \"mime\": \"application/pdf\"}]"}),
            'acaoAjaxAdicionarProcessoDocumento': 'acaoAjaxAdicionarProcessoDocumento',
            'ajaxSingle': 'acaoAjaxAdicionarProcessoDocumento',
            'AJAX:EVENTS_COUNT': '1'
        }

        response_step_1 = self.session.post(
            popup_url,
            data=data_step_1,
            headers=headers,
            verify=False)
        print(response_step_1)

        # STEP 2
        data_step_2 = {
            'AJAXREQUEST': containerId,
            'formularioUpload': 'formularioUpload',
            'cbTDDecoration:cbTD': '13',
            'ipDescDecoration:ipDesc': u'Petição',
            'ipNroDecoration:ipNro': '',
            'docPrincipalEditorTextArea': """"<p>peticao area</p>""",
            'context': '/pje',
            'cid': cid,
            'mimes': 'application/pdf',
            'mimesEhSizes': 'application/pdf:3.0',
            'j_id165:0:ordem': '1',
            'j_id165:0:descDoc': 'test',
            'j_id165:0:numeroDoc': '',
            'modalConfirmaLimparOpenedState': '',
            'modalErrosOpenedState': '',
            'quantidadeProcessoDocumento': '0',
            'javax.faces.ViewState': view_state['value'],
            'j_id165:0:tipoDoc': '13',
            'j_id165:0:j_id195': 'j_id165:0:j_id195',
            'ajaxSingle': 'j_id165:0:tipoDoc',
            'AJAX:EVENTS_COUNT': '1'
        }

        response_step_2 = self.session.post(
            popup_url, data=data_step_2,
            headers=headers,
            verify=False)
        print(response_step_2)

        # STEP 3
        data_step_3 = {
            'AJAXREQUEST': containerId,
            'formularioUpload': 'formularioUpload',
            'cbTDDecoration:cbTD': '13',
            'ipDescDecoration:ipDesc': u'Petição',
            'ipNroDecoration:ipNro': '',
            'docPrincipalEditorTextArea': """"<p>peticao area</p>""",
            'context': '/pje',
            'cid': cid,
            'mimes': 'application/pdf',
            'mimesEhSizes': 'application/pdf:3.0',
            'j_id165:0:ordem': '1',
            'j_id165:0:tipoDoc': '13',
            'j_id165:0:descDoc': 'test',
            'j_id165:0:numeroDoc': '',
            'modalConfirmaLimparOpenedState': '',
            'modalErrosOpenedState': '',
            'quantidadeProcessoDocumento': '0',
            'javax.faces.ViewState': view_state['value'],
            'j_id165:0:commandLinkAtualizarComboTipoDocumento': 'j_id165:0:commandLinkAtualizarComboTipoDocumento',
            'ajaxSingle': 'j_id165:0:commandLinkAtualizarComboTipoDocumento',
            'AJAX:EVENTS_COUNT': '1'
        }
        response_step_3 = self.session.post(
            popup_url, data=data_step_3,
            headers=headers,
            verify=False)
        print(response_step_3)

        # STEP 4

        data_step_4 = [
            ('formularioUpload', 'formularioUpload'),
            ('cbTDDecoration:cbTD', '13'),
            ('ipDescDecoration:ipDesc', 'Petição'),
            ('ipNroDecoration:ipNro', ''),
            ('docPrincipalEditorTextArea', '<p>peticao area</p>'),
            ('j_id152', 'Salvar'),
            ('context', '/pje'),
            ('cid', cid),
            ('mimes', 'application/pdf'),
            ('mimesEhSizes', 'application/pdf:3.0'),
            ('j_id165:0:ordem', '1'),
            ('j_id165:0:tipoDoc', '13'),
            ('j_id165:0:descDoc', 'test'),
            ('j_id165:0:numeroDoc', ''),
            ('modalConfirmaLimparOpenedState', ''),
            ('null', ''),
            ('j_id219', 'OK'),
            ('j_id220', 'Cancelar'),
            ('null', ''),
            ('modalErrosOpenedState', ''),
            ('null', ''),
            ('j_id226', 'OK'),
            ('null', ''),
            ('quantidadeProcessoDocumento', '0'),
            ('btn-assinador', 'Aguardando a classificação dos documentos'),
            ('javax.faces.ViewState', view_state['value']),
        ]

        headers['accept'] = "application/json"
        headers['content-type'] = 'multipart/form-data'
        headers['Host'] = 'pje.tjmg.jus.br'
        headers['Accept-Encoding'] = 'gzip, deflate, br'
        headers['Host'] = 'pje.tjmg.jus.br'
        headers['Origin'] = 'https://pje.tjmg.jus.br'
        headers['Pragma'] = "no-cache"
        headers['X-Requested-With'] = "XMLHttpRequest"

        with open('test.pdf', 'rb') as f:
            file = f.read()

        files = {'file': ('test.pdf', file, 'application/pdf')}

        response_step_4 = self.session.post('https://pje.tjmg.jus.br/pje/seam/resource/upload?cid={}'.format(cid), files=files, data=data_step_4)

        print(response_step_4)

        # STEP 5
        data_step_5 = {
            'AJAXREQUEST': containerId,
            'formularioUpload': 'formularioUpload',
            'cbTDDecoration:cbTD': '13',
            'ipDescDecoration:ipDesc': u'Petição',
            'ipNroDecoration:ipNro': '',
            'docPrincipalEditorTextArea': """"<p>peticao area</p>""",
            'context': '/pje',
            'cid': cid,
            'mimes': 'application/pdf',
            'mimesEhSizes': 'application/pdf:3.0',
            'j_id165:0:ordem': '1',
            'j_id165:0:tipoDoc': '13',
            'j_id165:0:descDoc': 'test',
            'j_id165:0:numeroDoc': '',
            'modalConfirmaLimparOpenedState': '',
            'modalErrosOpenedState': '',
            'quantidadeProcessoDocumento': '1',
            'javax.faces.ViewState': view_state['value'],
            'j_id165:0:commandLinkGravar': 'commandLinkGravar',
            'ajaxSingle': 'j_id165:0:commandLinkGravar',
            'AJAX:EVENTS_COUNT': '1'
        }
        response_step_5 = self.session.post(
            popup_url, data=data_step_5,
            verify=False)
        print(response_step_5)



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
    b = Bot(
        digital_user='admin',
        digital_password='123098skd123!98S_',
        authentication_type='api',
        session_key='4ZDHCoFOlmiWheeB6ZaqxUSNpG3kzHngBt9zQgvR.pje2ext-5'
    )
    b.parse('5101476-91.2017.8.13.0024', )
