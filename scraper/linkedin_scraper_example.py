from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy, ProxyType
from parsel import Selector
from bs4 import BeautifulSoup
from itertools import cycle
from selenium.common.exceptions import NoSuchElementException
from database_module import DatabaseConnector

import time
import link_generator
import proxy_generator
import traceback
import re
import logging
import threading
import numpy as np

chrome_settings = Options()
db = DatabaseConnector()


class LinkedinScraper:

    def __init__(self, email, password, category):
        super().__init__()

        self.email = email
        self.password = password
        self.category = category
        self.count = 1

        logging.basicConfig(
            handlers=[logging.FileHandler(
                './Logs/scraper.log', 'w', 'utf-8')],
            format = ': %(asctime)s : %(levelname)s : %(message)s : ',
        )

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.links = link_generator.generate(self.category)
        # self.proxy = proxy_generator.get_proxy()
        self.scrapedData = []

        # try:
        #     prox = Proxy()
        #     prox.proxy_type = ProxyType.MANUAL
        #     prox.http_proxy = self.proxy
        #     capabilities = webdriver.DesiredCapabilities.CHROME
        #     prox.add_to_capabilities(capabilities)
        #     self.driver = webdriver.Chrome(
        #         chrome_options=chrome_settings, desired_capabilities=capabilities)

        # except Exception as e:
        #     self.logger.critical("Driver Error: " + str(e))

        self.driver = webdriver.Chrome(
                chrome_options=chrome_settings)

    def openLinkedin(self):

        self.logger.info("Logging into Linkedin....................")

        try:
            self.driver.get("https://www.linkedin.com/login")
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username")))
            email_element = self.driver.find_element_by_id("username")
            email_element.send_keys(self.email)
            password_element = self.driver.find_element_by_id("password")
            password_element.send_keys(self.password)
            self.driver.find_element_by_tag_name("button").click()

        except Exception as e:
            self.logger.critical("Error: " + str(e))

    def scrape(self):

        for page in range(link_generator.no_of_pages):
            for link in self.links[page]:

                profile_pic = ''
                about = ''
                main_exp_data = ''
                name = ''
                title = ''
                location = ''
                skills = ''

                data_profile = {}
                data_profile['category'] = self.category
                self.logger.info("Profile #"+str(self.count))
                try:

                    data_profile['URl'] = link
                    self.driver.get(link)
                    self.logger.info(
                        "Waiting for page to completely load.................")
                    try:
                        element = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.ID, "profile-nav-item")))
                    except Exception as e:
                        self.logger.error(str(e))

                    time.sleep(5)

                    y_coord = 500
                    for i in range(5):
                        self.driver.execute_script(
                            "window.scrollTo(0, " + str(y_coord) + ");")
                        time.sleep(2)
                        y_coord += 500

                    source = self.driver.page_source

                except Exception as e:
                    self.logger.error("Error while waiting " + str(e))

                self.logger.info("..................Page loaded")

                time.sleep(1)

                # Profile Picture and About data

                soup = BeautifulSoup(source, 'html.parser')

                try:
                    image = soup.findAll(
                        "img", {"class": "pv-top-card__photo"})
                    profile_pic = image[0]['src']

                except NoSuchElementException as e:
                    self.logger.warn(str(e))

                except Exception as e:
                    self.logger.error(
                        "Error while scraping Profile Picture: " + str(e))

                data_profile['image_url'] = profile_pic

                try:
                    about_elements = soup.findAll(
                        "p", {"class": "pv-about__summary-text"})

                    for element in about_elements[0].children:
                        try:
                            if '...' in element.text:
                                break
                            about = about + element.text.strip()

                        except:
                            continue

                except (NoSuchElementException, IndexError) as e:
                    self.logger.warn(str(e))

                except Exception as e:
                    self.logger.error("Error while scraping About: " + str(e))

                data_profile['about'] = about

                # Experience data

                try:
                    experience_div = soup.find(
                        "div", {"class": "pv-profile-section-pager ember-view"})
                    experience_section = experience_div.find(
                        "section", {"class": "pv-profile-section"})
                    lists = experience_section.find("ul").findAll("li")

                except NoSuchElementException as e:
                    self.logger.warn(str(e))

                except Exception as e:
                    self.logger.error(
                        "Error while scraping Experience " + str(e))
                    lists = []

                exp = []
                for element in lists:
                    data = element.text
                    if(data == "/n"):
                        continue
                    else:
                        exp.append(data)

                expdata = []
                for element in exp:
                    ls = element.splitlines()
                    for str1 in ls:
                        if(str1.isspace() or str1 == '' or str1.strip() == 'see more' or str1 == '...'):
                            continue
                        else:
                            main_exp_data = main_exp_data + str1.strip()

                main_exp_data = re.sub('•', '', main_exp_data)
                main_exp_data = re.sub('  ', '', main_exp_data)
                data_profile['experience'] = main_exp_data

                # Name, Title, Location
                try:
                    intro = soup.find("div", {"class": "flex-1 mr5"})
                    name = intro.ul.li.text.strip()
                    title = intro.h2.text.strip()
                    ul = intro.findAll("ul")
                    location = ul[1].li.text.strip()

                except NoSuchElementException as e:
                    self.logger.warn(str(e))

                except Exception as e:
                    self.logger.error(
                        "Error while scraping name, title, location " + str(e))

                data_profile['name'] = name
                data_profile['title'] = title
                data_profile['location'] = location

                try:
                    try:
                        self.driver.find_element_by_xpath(
                            "//button[@class='pv-profile-section__card-action-bar pv-skills-section__additional-skills artdeco-container-card-action-bar artdeco-button artdeco-button--tertiary artdeco-button--3 artdeco-button--fluid']").click()

                    except NoSuchElementException as e:
                        self.logger.warn(str(e))

                    except Exception as e:
                        self.logger.error("Error: " + str(e))

                    sel = Selector(text=self.driver.page_source)

                    skills = str(sel.xpath(
                        '//*[@class="pv-skill-category-entity__name-text t-16 t-black t-bold"]/text()').extract())

                    skills = re.sub('\n', '', skills)
                    skills = re.sub('  ', '', skills)

                    data_profile['skills'] = skills

                except NoSuchElementException as e:
                    self.logger.warn(str(e))

                except Exception as e:
                    self.logger.error("error in skills " + str(e))

                self.logger.info(str(data_profile))

                if (data_profile['about'] == '' and data_profile['experience'] == '' and data_profile['skills'] == ''):
                    self.logger.critical(
                        "Scraper has stopped working for some reason. Please check logs. \n You should also check "+data_profile['URl'])
                    exit()

                if(
                    data_profile['category'] == 'Administração' or 
                    data_profile['category'] == 'Administração Pública' or 
                    data_profile['category'] == 'Agronegócios e Agropecuária' or 
                    data_profile['category'] == 'Ciências Aeronáuticas' or 
                    data_profile['category'] == 'Ciências Atuariais' or 
                    data_profile['category'] == 'Ciências Contábeis' or 
                    data_profile['category'] == 'Ciências Econômicas' or 
                    data_profile['category'] == 'Comércio Exterior' or 
                    data_profile['category'] == 'Defesa e Gestão Estratégica Internacional' or 
                    data_profile['category'] == 'Gastronomia' or 
                    data_profile['category'] == 'Gestão Comercial' or 
                    data_profile['category'] == 'Gestão de Recursos Humanos' or 
                    data_profile['category'] == 'Gestão de Segurança Privada' or 
                    data_profile['category'] == 'Gestão de Seguros' or 
                    data_profile['category'] == 'Gestão de Turismo' or 
                    data_profile['category'] == 'Gestão Financeira' or 
                    data_profile['category'] == 'Gestão Pública' or 
                    data_profile['category'] == 'Hotelaria' or 
                    data_profile['category'] == 'Logística' or 
                    data_profile['category'] == 'Marketing' or 
                    data_profile['category'] == 'Negócios Imobiliários' or 
                    data_profile['category'] == 'Pilotagem profissional de aeronaves' or 
                    data_profile['category'] == 'Processos Gerenciais' or 
                    data_profile['category'] == 'Segurança Pública' or 
                    data_profile['category'] == 'Turismo'):

                    db.insertDB('Administracao', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'], data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                elif(
                    data_profile['category'] == 'Animação' or 
                    data_profile['category'] == 'Arquitetura e Urbanismo' or 
                    data_profile['category'] == 'Artes Visuais' or 
                    data_profile['category'] == 'Comunicação das Artes do Corpo' or 
                    data_profile['category'] == 'Conservação e Restauro' or 
                    data_profile['category'] == 'Dança' or 
                    data_profile['category'] == 'Design' or 
                    data_profile['category'] == 'Design de Games' or 
                    data_profile['category'] == 'Design de Interiores' or 
                    data_profile['category'] == 'Design de Moda' or 
                    data_profile['category'] == 'Fotografia' or 
                    data_profile['category'] == 'História da Arte' or 
                    data_profile['category'] == 'Jogos Digitais' or 
                    data_profile['category'] == 'Luteria' or 
                    data_profile['category'] == 'Música' or 
                    data_profile['category'] == 'Produção Cênica' or 
                    data_profile['category'] == 'Produção Fonográfica' or 
                    data_profile['category'] == 'Teatro'
                ):
                    db.insertDB('Arte e Desing', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                elif(
                    data_profile['category'] == 'Agroecologia' or 
                    data_profile['category'] == 'Agronomia' or 
                    data_profile['category'] == 'Alimentos' or 
                    data_profile['category'] == 'Biocombustíveis' or 
                    data_profile['category'] == 'Biotecnologia' or 
                    data_profile['category'] == 'Biotecnologia e Bioquímica' or 
                    data_profile['category'] == 'Ciência e Tecnologia de Alimentos' or 
                    data_profile['category'] == 'Ciências Agrárias' or 
                    data_profile['category'] == 'Ciências Biológicas' or 
                    data_profile['category'] == 'Ciências Naturais e Exatas' or 
                    data_profile['category'] == 'Ecologia' or 
                    data_profile['category'] == 'Geofísica' or 
                    data_profile['category'] == 'Geologia' or 
                    data_profile['category'] == 'Gestão Ambiental' or 
                    data_profile['category'] == 'Medicina Veterinária' or 
                    data_profile['category'] == 'Meteorologia' or 
                    data_profile['category'] == 'Oceanografia' or 
                    data_profile['category'] == 'Produção de Bebidas' or 
                    data_profile['category'] == 'Produção Sucroalcooleira' or 
                    data_profile['category'] == 'Rochas Ornamentais' or 
                    data_profile['category'] == 'Zootecnia'
                ):
                    db.insertDB('Ciências Biológicas e da Terra', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                
                elif(
                    data_profile['category'] == 'Informática' or 
                    data_profile['category'] == 'Astronomia' or 
                    data_profile['category'] == 'Banco de Dados' or 
                    data_profile['category'] == 'Ciência da Computação' or 
                    data_profile['category'] == 'Ciência e Tecnologia' or 
                    data_profile['category'] == 'Computação' or 
                    data_profile['category'] == 'Estatística' or 
                    data_profile['category'] == 'Física' or 
                    data_profile['category'] == 'Gestão da Tecnologia da Informação' or 
                    data_profile['category'] == 'Informática Biomédica' or 
                    data_profile['category'] == 'Matemática' or 
                    data_profile['category'] == 'Nanotecnologia' or 
                    data_profile['category'] == 'Química' or 
                    data_profile['category'] == 'Redes de Computadores' or 
                    data_profile['category'] == 'Segurança da Informação' or 
                    data_profile['category'] == 'Sistemas de Informação' or 
                    data_profile['category'] == 'Sistemas para Internet'
                ):
                    db.insertDB('Análise e Desenvolvimento de Sistemas', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                elif(
                    data_profile['category'] == 'Arqueologia' or 
                    data_profile['category'] == 'Ciências do Consumo' or 
                    data_profile['category'] == 'Ciências Humanas' or 
                    data_profile['category'] == 'Ciências Sociais' or 
                    data_profile['category'] == 'Cooperativismo' or 
                    data_profile['category'] == 'Direito' or 
                    data_profile['category'] == 'Escrita Criativa' or 
                    data_profile['category'] == 'Estudos de Gênero e Diversidade' or 
                    data_profile['category'] == 'Filosofia' or 
                    data_profile['category'] == 'Geografia' or 
                    data_profile['category'] == 'Gestão de Cooperativas' or 
                    data_profile['category'] == 'História' or 
                    data_profile['category'] == 'Letras' or 
                    data_profile['category'] == 'Libras' or 
                    data_profile['category'] == 'Linguística' or 
                    data_profile['category'] == 'Museologia' or 
                    data_profile['category'] == 'Pedagogia' or 
                    data_profile['category'] == 'Psicopedagogia' or 
                    data_profile['category'] == 'Relações Internacionais' or 
                    data_profile['category'] == 'Serviço Social' or 
                    data_profile['category'] == 'Serviços Judiciários e Notariais' or 
                    data_profile['category'] == 'Teologia' or 
                    data_profile['category'] == 'Tradutor e Intérprete'
                ):
                    db.insertDB('Ciências Sociais e Humanas', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                
                elif(
                    data_profile['category'] == 'Arquivologia' or 
                    data_profile['category'] == 'Biblioteconomia' or 
                    data_profile['category'] == 'Cinema e Audiovisual' or 
                    data_profile['category'] == 'Comunicação em Mídias Digitais' or 
                    data_profile['category'] == 'Comunicação Institucional' or 
                    data_profile['category'] == 'Comunicação Organizacional' or 
                    data_profile['category'] == 'Educomunicação' or 
                    data_profile['category'] == 'Estudos de Mídia' or 
                    data_profile['category'] == 'Eventos' or 
                    data_profile['category'] == 'Gestão da Informação' or 
                    data_profile['category'] == 'Jornalismo' or 
                    data_profile['category'] == 'Produção Audiovisual' or 
                    data_profile['category'] == 'Produção Cultural' or 
                    data_profile['category'] == 'Produção Editorial' or 
                    data_profile['category'] == 'Produção Multimídia' or 
                    data_profile['category'] == 'Produção Publicitária' or 
                    data_profile['category'] == 'Publicidade e Propaganda' or 
                    data_profile['category'] == 'Rádio TV e Internet' or 
                    data_profile['category'] == 'Relações Públicas' or 
                    data_profile['category'] == 'Secretariado' or 
                    data_profile['category'] == 'Secretariado Executivo'
                ):
                    db.insertDB('Comunicação e Informação', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                
                elif(
                    data_profile['category'] == 'Agrimensura' or 
                    data_profile['category'] == 'Aquicultura' or 
                    data_profile['category'] == 'Automação Industrial' or 
                    data_profile['category'] == 'Construção Civil' or 
                    data_profile['category'] == 'Construção Naval' or 
                    data_profile['category'] == 'Eletrônica Industrial' or 
                    data_profile['category'] == 'Eletrotécnica Industrial' or 
                    data_profile['category'] == 'Energias Renováveis' or 
                    data_profile['category'] == 'Engenharia Acústica' or 
                    data_profile['category'] == 'Engenharia Aeronáutica' or 
                    data_profile['category'] == 'Engenharia Agrícola' or 
                    data_profile['category'] == 'Engenharia Ambiental e Sanitária' or 
                    data_profile['category'] == 'Engenharia Biomédica' or 
                    data_profile['category'] == 'Engenharia Bioquímica or  de Bioprocessos e Biotecnologia' or 
                    data_profile['category'] == 'Engenharia Cartográfica e de Agrimensura' or 
                    data_profile['category'] == 'Engenharia Civil' or 
                    data_profile['category'] == 'Engenharia da Computação' or 
                    data_profile['category'] == 'Engenharia de Alimentos' or 
                    data_profile['category'] == 'Engenharia de Biossistemas' or 
                    data_profile['category'] == 'Engenharia de Controle e Automação' or 
                    data_profile['category'] == 'Engenharia de Energia' or 
                    data_profile['category'] == 'Engenharia de Inovação' or 
                    data_profile['category'] == 'Engenharia de Materiais' or 
                    data_profile['category'] == 'Engenharia de Minas' or 
                    data_profile['category'] == 'Engenharia de Pesca' or 
                    data_profile['category'] == 'Engenharia de Petróleo' or 
                    data_profile['category'] == 'Engenharia de Produção' or 
                    data_profile['category'] == 'Engenharia de Segurança no Trabalho' or 
                    data_profile['category'] == 'Engenharia de Sistemas' or 
                    data_profile['category'] == 'Engenharia de Software' or 
                    data_profile['category'] == 'Engenharia de Telecomunicações' or 
                    data_profile['category'] == 'Engenharia de Transporte e da Mobilidade' or 
                    data_profile['category'] == 'Engenharia Elétrica' or 
                    data_profile['category'] == 'Engenharia Eletrônica' or 
                    data_profile['category'] == 'Engenharia Física' or 
                    data_profile['category'] == 'Engenharia Florestal' or 
                    data_profile['category'] == 'Engenharia Hídrica' or 
                    data_profile['category'] == 'Engenharia Industrial Madeireira' or 
                    data_profile['category'] == 'Engenharia Mecânica' or 
                    data_profile['category'] == 'Engenharia Mecatrônica' or 
                    data_profile['category'] == 'Engenharia Metalúrgica' or 
                    data_profile['category'] == 'Engenharia Naval' or 
                    data_profile['category'] == 'Engenharia Nuclear' or 
                    data_profile['category'] == 'Engenharia Química' or 
                    data_profile['category'] == 'Engenharia Têxtil' or 
                    data_profile['category'] == 'Fabricação Mecânica' or 
                    data_profile['category'] == 'Geoprocessamento' or 
                    data_profile['category'] == 'Gestão da Produção Industrial' or 
                    data_profile['category'] == 'Gestão da Qualidade' or 
                    data_profile['category'] == 'Irrigação e Drenagem' or 
                    data_profile['category'] == 'Manutenção de aeronaves' or 
                    data_profile['category'] == 'Manutenção Industrial' or 
                    data_profile['category'] == 'Materiais' or 
                    data_profile['category'] == 'Mecatrônica Industrial' or 
                    data_profile['category'] == 'Mineração' or 
                    data_profile['category'] == 'Papel e Celulose' or 
                    data_profile['category'] == 'Petróleo e Gás' or 
                    data_profile['category'] == 'Processos Metalúrgicos' or 
                    data_profile['category'] == 'Processos Químicos' or 
                    data_profile['category'] == 'Produção Têxtil' or 
                    data_profile['category'] == 'Saneamento Ambiental' or 
                    data_profile['category'] == 'Segurança no Trabalho' or 
                    data_profile['category'] == 'Silvicultura' or 
                    data_profile['category'] == 'Sistemas Biomédicos' or 
                    data_profile['category'] == 'Sistemas de Telecomunicações' or 
                    data_profile['category'] == 'Sistemas Elétricos' or 
                    data_profile['category'] == 'Sistemas Embarcados' or 
                    data_profile['category'] == 'Transporte'
                    ):
                        db.insertDB('Engenharia e Produção', data_profile['category'], data_profile['URl'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                    
                elif(
                    data_profile['category'] == 'Biomedicina' or 
                    data_profile['category'] == 'Educação Física' or 
                    data_profile['category'] == 'Enfermagem' or 
                    data_profile['category'] == 'Esporte' or 
                    data_profile['category'] == 'Estética e Cosmética' or 
                    data_profile['category'] == 'Farmácia' or 
                    data_profile['category'] == 'Fisioterapia' or 
                    data_profile['category'] == 'Fonoaudiologia' or 
                    data_profile['category'] == 'Gerontologia' or 
                    data_profile['category'] == 'Gestão Desportiva e de Lazer' or 
                    data_profile['category'] == 'Gestão em Saúde' or 
                    data_profile['category'] == 'Gestão Hospitalar' or 
                    data_profile['category'] == 'Medicina' or 
                    data_profile['category'] == 'Musicoterapia' or 
                    data_profile['category'] == 'Naturologia' or 
                    data_profile['category'] == 'Nutrição' or 
                    data_profile['category'] == 'Obstetrícia' or 
                    data_profile['category'] == 'Odontologia' or 
                    data_profile['category'] == 'Oftálmica' or 
                    data_profile['category'] == 'Optometria' or 
                    data_profile['category'] == 'Psicologia' or 
                    data_profile['category'] == 'Quiropraxia' or 
                    data_profile['category'] == 'Radiologia' or 
                    data_profile['category'] == 'Saúde Coletiva' or 
                    data_profile['category'] == 'Terapia Ocupacional'
                    ):
                        db.insertDB('saúde', data_profile['URl'], data_profile['category'], data_profile['image_url'], data_profile['about'],
                                data_profile['experience'], data_profile['name'], data_profile['title'], data_profile['location'], data_profile['skills'])
                
                self.count += 1
                self.scrapedData.append(data_profile)

    def start(self):

        self.openLinkedin()
        self.scrape()
        self.driver.quit()
        self.logger.info("Scraping completed for "+self.category)



class Batch:

    def __init__(self, subcategories, account):
        super().__init__()
        self.subcategories = subcategories
        self.account = account

    def runBatch(self):

        for subcategory in self.subcategories:
            linkedinscraper = LinkedinScraper(self.account['email'], self.account['password'], subcategory)
            linkedinscraper.start()


if __name__ == "__main__":

    accounts = [
        {
            'email' : "enter email",
            'password' : "enter password"
        },
        {
            'email' : "enter email",
            'password' : "enter password"
        },
    ]

    categories = [
# 'Administração',
# 'Administração Pública',
# 'Agronegócios e Agropecuária',
# 'Ciências Aeronáuticas',
# 'Ciências Atuariais',
# 'Ciências Contábeis',
# 'Ciências Econômicas',
# 'Comércio Exterior',
# 'Defesa e Gestão Estratégica Internacional',
# 'Gastronomia',
# 'Gestão Comercial',
# 'Gestão de Recursos Humanos',
# 'Gestão de Segurança Privada',
# 'Gestão de Seguros',
# 'Gestão de Turismo',
# 'Gestão Financeira',
# 'Gestão Pública',
# 'Hotelaria',
# 'Logística',
# 'Marketing',
# 'Negócios Imobiliários',
# 'Pilotagem profissional de aeronaves',
# 'Processos Gerenciais',
# 'Segurança Pública',
# 'Turismo',

# 'Animação',
# 'Arquitetura e Urbanismo',
# 'Artes Visuais',
# 'Comunicação das Artes do Corpo',
# 'Conservação e Restauro',
# 'Dança',
# 'Design',
# 'Design de Games',
# 'Design de Interiores',
# 'Design de Moda',
# 'Fotografia',
# 'História da Arte',
# 'Jogos Digitais',
# 'Luteria',
# 'Música',
# 'Produção Cênica',
# 'Produção Fonográfica',
# 'Teatro',

# # 'Agroecologia',
# 'Agronomia',
# 'Alimentos',
# 'Biocombustíveis',
# 'Biotecnologia',
# 'Biotecnologia e Bioquímica',
# 'Ciência e Tecnologia de Alimentos',
# 'Ciências Agrárias',
# 'Ciências Biológicas',
# 'Ciências Naturais e Exatas',
# 'Ecologia',
# 'Geofísica',
# 'Geologia',
# 'Gestão Ambiental',
# 'Medicina Veterinária',
# 'Meteorologia',
# 'Oceanografia',
# 'Produção de Bebidas',
# 'Produção Sucroalcooleira',
# 'Rochas Ornamentais',
# 'Zootecnia',

# 'Informática',
# 'Astronomia',
# 'Banco de Dados',
# 'Ciência da Computação',
# 'Ciência e Tecnologia',
# 'Computação',
# 'Estatística',
# 'Física',
# 'Gestão da Tecnologia da Informação',
# 'Informática Biomédica',
# 'Matemática',
# 'Nanotecnologia',
# 'Química',
# 'Redes de Computadores',
# 'Segurança da Informação',
# 'Sistemas de Informação',
# 'Sistemas para Internet',

# 'Arqueologia',
# 'Ciências do Consumo',
# 'Ciências Humanas',
# 'Ciências Sociais',
# 'Cooperativismo',
# 'Direito',
# 'Escrita Criativa',
# 'Estudos de Gênero e Diversidade',
# 'Filosofia',
# 'Geografia',
# 'Gestão de Cooperativas',
# 'História',
# 'Letras',
# 'Libras',
# 'Linguística',
# 'Museologia',
# 'Pedagogia',
# 'Psicopedagogia',
# 'Relações Internacionais',
# 'Serviço Social',
# 'Serviços Judiciários e Notariais',
# 'Teologia',
# 'Tradutor e Intérprete',

# 'Arquivologia',
# 'Biblioteconomia',
# 'Cinema e Audiovisual',
# 'Comunicação em Mídias Digitais',
# 'Comunicação Institucional',
# 'Comunicação Organizacional',
# 'Educomunicação',
# 'Estudos de Mídia',
# 'Eventos',
# 'Gestão da Informação',
# 'Jornalismo',
# 'Produção Audiovisual',
# 'Produção Cultural',
# 'Produção Editorial',
# 'Produção Multimídia',
# 'Produção Publicitária',
# 'Publicidade e Propaganda',
# 'Rádio, TV e Internet',
# 'Relações Públicas',
# 'Secretariado',
# 'Secretariado Executivo',

# 'Agrimensura',
# 'Aquicultura',
# 'Automação Industrial',
# 'Construção Civil',
# 'Construção Naval',
# 'Eletrônica Industrial',
# 'Eletrotécnica Industrial',
# 'Energias Renováveis',
# 'Engenharia Acústica',
# 'Engenharia Aeronáutica',
# 'Engenharia Agrícola',
# 'Engenharia Ambiental e Sanitária',
# 'Engenharia Biomédica',
# 'Engenharia Bioquímica, de Bioprocessos e Biotecnologia',
# 'Engenharia Cartográfica e de Agrimensura',
# 'Engenharia Civil',
# 'Engenharia da Computação',
# 'Engenharia de Alimentos',
# 'Engenharia de Biossistemas',
# 'Engenharia de Controle e Automação',
# 'Engenharia de Energia',
# 'Engenharia de Inovação',
# 'Engenharia de Materiais',
# 'Engenharia de Minas',
# 'Engenharia de Pesca',
# 'Engenharia de Petróleo',
# 'Engenharia de Produção',
# 'Engenharia de Segurança no Trabalho',
# 'Engenharia de Sistemas',
# 'Engenharia de Software',
# 'Engenharia de Telecomunicações',
# 'Engenharia de Transporte e da Mobilidade',
# 'Engenharia Elétrica',
# 'Engenharia Eletrônica',
# 'Engenharia Física',
# 'Engenharia Florestal',
# 'Engenharia Hídrica',
# 'Engenharia Industrial Madeireira',
'Engenharia Mecânica',
'Engenharia Mecatrônica',
'Engenharia Metalúrgica',
'Engenharia Naval',
'Engenharia Nuclear',
'Engenharia Química',
'Engenharia Têxtil',
'Fabricação Mecânica',
'Geoprocessamento',
'Gestão da Produção Industrial',
'Gestão da Qualidade',
'Irrigação e Drenagem',
'Manutenção de aeronaves',
'Manutenção Industrial',
'Materiais',
'Mecatrônica Industrial',
'Mineração',
'Papel e Celulose',
'Petróleo e Gás',
'Processos Metalúrgicos',
'Processos Químicos',
'Produção Têxtil',
'Saneamento Ambiental',
'Segurança no Trabalho',
'Silvicultura',
'Sistemas Biomédicos',
'Sistemas de Telecomunicações',
'Sistemas Elétricos',
'Sistemas Embarcados',
'Transporte',

'Biomedicina',
'Educação Física',
'Enfermagem',
'Esporte',
'Estética e Cosmética',
'Farmácia',
'Fisioterapia',
'Fonoaudiologia',
'Gerontologia',
'Gestão Desportiva e de Lazer',
'Gestão em Saúde',
'Gestão Hospitalar',
'Medicina',
'Musicoterapia',
'Naturologia',
'Nutrição',
'Obstetrícia',
'Odontologia',
'Oftálmica',
'Optometria',
'Psicologia',
'Quiropraxia',
'Radiologia',
'Saúde Coletiva',
'Terapia Ocupacional'
 ]
 
    no_of_batches = 1

    if no_of_batches <= len(categories):

        for index, subcategories in enumerate(np.array_split(np.array(categories), no_of_batches)):

            account = accounts[(index) % len(accounts)]
            batch = Batch(subcategories.tolist(), account)
            threading.Thread(target=batch.runBatch).start()
    else:
        print("Number of batches should be less than the list")
