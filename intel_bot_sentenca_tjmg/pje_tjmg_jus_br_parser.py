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

            session.post(self.digital_api_url + login_admin_url, data=login_data)

            self.response_cookies = session.get(self.digital_api_url + 'digital_api/get_pje_cookie/?url={}'.format(LOGIN_URL)).json()

            if isinstance(self.response_cookies, dict):
                if self.response_cookies.get('status', '') == 'fail':
                    raise Exception('Login to website failed. Please check API server. Line 75.')

            session_bot.cookies.set(self.response_cookies[0]['name'], self.response_cookies[0]['value'])

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
                filter_dict[re.search("'(.*?)'", item).group(1)] = re.search("':(.*?)$", item) \
                                                                     .group(1) \
                                                                     .replace("'", "") \
                                                                     .replace('}', '')
        except:
            pass
        return filter_dict

    def parse(self, number):
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
            response_peticionar = self.session.get(peticionar_url, headers=headers, verify=False)
        except Exception:
            raise Exception('Connection aborted. Line: 241.')

        soup = BeautifulSoup(response_peticionar.content, 'html.parser')
        jds = [i for i in soup.find_all('script') if 'concluirPeticionamento' in str(i)][0]['id']

        view_state = soup.find(id='javax.faces.ViewState')
        cid = soup.find("input", {"name":"cid"})['value']


        try:
            select_cb = soup.find(id='cbTDDecoration:cbTD')['onchange']

        except Exception:
            raise Exception('Search number was not found. Line: 249.')

        filter_dict = self.parse_to_json(select_cb)
        # peticaoPopUp

        data = {
            'AJAXREQUEST': '_viewRoot',
            'formularioUpload': 'formularioUpload',
            'cbTDDecoration:cbTD': '13',
            'ipDescDecoration:ipDesc': u'Petição',
            'ipNroDecoration:ipNro': '',
            'docPrincipalEditorTextArea': """<p>peticao area</p>""",
            'context': '/pje',
            'cid': cid,
            'mimes': 'application/pdf',
            'mimesEhSizes': 'application/pdf:3.0',
            'j_id165:0:ordem': '1',
            'j_id165:0:tipoDoc': '13',
            'j_id165:0:descDoc': '1bf2c6d_0010492-57.2018.5.03.0181',
            'j_id165:0:numeroDoc': '',
            'modalConfirmaLimparOpenedState': '',
            'modalErrosOpenedState': '',
            'quantidadeProcessoDocumento': '1',
            'javax.faces.ViewState': view_state['value'],
            'j_id147': 'j_id147',
            'AJAX:EVENTS_COUNT': '1'
        }

        popup_url = 'https://pje.tjmg.jus.br/pje/Processo/CadastroPeticaoAvulsa/peticaoPopUp.seam'
        popup = self.session.post(popup_url, data=data, headers=headers, verify=False)

        soup = BeautifulSoup(popup.text, 'html.parser')
        poup_data = str(soup.find_all('script')[-1]).split()[5].split('&')

        cookies = self.session.cookies.get_dict()

        url = 'http://localhost:8800/pjeOffice/requisicao/?r=%7B%22aplicacao%22%3A%22PJe%22%2C%22servidor%22%3A%22https%3A%2F%2Fpje.tjmg.jus.br%2Fpje%22%2C%22sessao%22%3A%22f5_cspm%3D1234%3B%20f5_cspm%3D1234%3B%20f5_cspm%3D1234%3B%20MO%3DP%3B%20JSESSIONID%3D{JSESSIONID}%3B%20%22%2C%22codigoSeguranca%22%3A%22EDnQ%2B4U3cujIQra0RRPWqSHpT3dsNgZWpa66Ywp8l0baGFpanQt%2Bocv7m9wV1hDEFvxhkBma3Da8%2B29TQl7HyI9t7aNQHMxOVHx8eldEb0M3RacRKbfjJ8QGx7BFhGIVAOTpW%2F8QgvMdfL%2B4QenHXjXl2CaWOvtQCTqRWtAkm4zJZmxQeZ93Qnx40CiNEw%2F%2BuZD%2B7HQ8y4RVr6ulUaXy6Tv8T%2FJNa%2B7cc3zIfkLJzz%2B9GksmM03cOMU6vBDnHK%2BCNzc2nX1Rvy%2FBrRv5szrC0gsCgMXOwAilXpH2Dhi43qmxuDe7ZEBwZJYmXG%2FsJb1P2dkG%2B%2F3GnuYxXnyuiUK1TQ%3D%3D%22%2C%22tarefaId%22%3A%22cnj.assinadorHash%22%2C%22tarefa%22%3A%22%7B%5C%22algoritmoAssinatura%5C%22%3A%5C%22ASN1MD5withRSA%5C%22%2C%5C%22modoTeste%5C%22%3A%5C%22false%5C%22%2C%5C%22uploadUrl%5C%22%3A%5C%22%2FarquivoAssinadoUpload.seam%3Faction%3DpeticionamentoAction%26cid%3D{CID}%26mo%3DP%5C%22%2C%5C%22arquivos%5C%22%3A%5B%7B%5C%22id%5C%22%3A%5C%22{ID1}%5C%22%2C%5C%22codIni%5C%22%3A%5C%22{codIni1}%5C%22%2C%5C%22hash%5C%22%3A%5C%22{HASH1}%5C%22%2C%5C%22isBin%5C%22%3A%5C%22false%5C%22%7D%2C%7B%5C%22id%5C%22%3A%5C%226{ID2}%5C%22%2C%5C%22codIni%5C%22%3A%5C%22{codIni2}%5C%22%2C%5C%22hash%5C%22%3A%5C%22{HASH2}%5C%22%2C%5C%22isBin%5C%22%3A%5C%22true%5C%22%7D%5D%7D%22%7D&u={timestamp}'.format(
            JSESSIONID=cookies['JSESSIONID'],
            timestamp=int(time.time() * 1000),
            CID=cid,
            ID1=poup_data[0].split('=')[-1],
            codIni1=poup_data[1].split('=')[-1],
            HASH1=poup_data[2].split('=')[-1],
            ID2=poup_data[3].split('=')[-1],
            codIni2=poup_data[4].split('=')[-1],
            HASH2=poup_data[5].split('=')[-1]
        )


        sign_doc = self.session.get(url)

        popup_data = {
            'AJAXREQUEST': '_viewRoot',
            jds.split(':')[0]: jds.split(':')[0],
            'autoScroll': '',
            'javax.faces.ViewState': view_state['value'],
            jds: jds,
            'AJAX:EVENTS_COUNT': '1'
        }
        headers['Referer'] = peticionar_url
        headers['Origin'] = 'https://pje.tjmg.jus.br'
        response = self.session.post(popup_url, data=popup_data, headers=headers)
        print(response)

        # filter_dict['AJAXREQUEST'] = data['AJAXREQUEST']
        # filter_dict['ipDescDecoration:ipDesc'] = 'Petição'
        # filter_dict['javax.faces.ViewState'] = view_state['value']
        # filter_dict['cbTDDecoration:cbTD'] = 13
        # filter_dict['AJAX:EVENTS_COUNT'] = 1
        # filter_dict['ipNroDecoration:ipNro'] = ''
        # filter_dict['docPrincipalEditorTextArea'] = u'<p>peticao area</p>'
        # filter_dict['context'] = '/pje'
        # filter_dict['mimes'] = 'application/pdf'
        # filter_dict['mimesEhSizes'] = 'application/pdf:3.0'
        # filter_dict['modalConfirmaLimparOpenedState'] = ''
        # filter_dict['modalErrosOpenedState'] = ''
        # filter_dict['quantidadeProcessoDocumento'] = 0

        # try:
        #     save_peticao = self.session.post(
        #         peticionar_url,
        #         data=filter_dict,
        #         headers=headers,
        #         verify=False)
        # except Exception:
        #     raise Exception('Connection aborted. Line: 256.')

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
    b = Bot(
        digital_user='admin',
        digital_password='123098skd123!98S_',
        authentication_type='api',
        session_key='4ZDHCoFOlmiWheeB6ZaqxUSNpG3kzHngBt9zQgvR.pje2ext-5'
    )
    b.parse('5101476-91.2017.8.13.0024',)
