#-*- coding: utf-8 -*-

from models import ndbSpremembaCene, ndbTecaj, ndbTimeMarker
import webapp2
import urllib2
import logging
from HTMLParser import HTMLParser
from google.appengine.api import mail
from datetime import datetime, timedelta
import jinja2
import os
import json

url_poraba = ("http://www.mgrt.gov.si/si/delovna_podrocja/notranji_trg/"
              "sektor_za_preskrbo_nadzor_cen_in_varstvo_konkurence/"
              "cene_naftnih_derivatov/")

url_tecaj_usd = "http://www.bsi.si/_data/tecajnice/dtecbs.xml"
url_tecaj_RBOB_gasoline = "http://markets.ft.com/research/Markets/Tearsheets/Summary?s=3334534"

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class InitHandler(webapp2.RequestHandler):
    @staticmethod
    def get(self):

        init = ndbSpremembaCene()
        init.drobnoprodajna_cena = [0.0, 0.0, 0.0, 0.0]
        init.trosarina = [0.0, 0.0, 0.0, 0.0]

        init.put()


class IndexHandler(webapp2.RedirectHandler):
    def get(self):

        imena_derivatov = ['Bencin 95-oktanski', 'Bencin 98-oktanski', 'Dizel', 'Kurilno olje']
        imena_postavk = ['Ostalo', 'Trosarina', 'DDV', 'Marza', 'Clanarina']

        db_zadnja_sprememba = ndbSpremembaCene.query_cene(None).fetch(2)[0]
        db_predzadnja_sprememba = ndbSpremembaCene.query_cene(None).fetch(2)[1]

        db_timemark = ndbTimeMarker.query().fetch()[0]
        db_tecaji_stari = ndbTecaj.query(ndbTecaj.date > db_timemark.date - timedelta(days=14),
                                         ndbTecaj.date < db_timemark.date).fetch()

        db_tecaji_aktualni = ndbTecaj.query(ndbTecaj.date > db_timemark.date).fetch()
        db_cene = ndbSpremembaCene.query_cene(None).fetch()

        const_marze = [0.08530, 0.08530, 0.07998, 0.05265]
        const_zrsbr = [0.01222, 0.01222, 0.01166, 0.01166]
        const_ddv = 1.22
        subpage = self.request.path

        json_torta = {
            'cols':
            [
                {'label': 'Postavka', 'type': 'string'},
                {'label': 'Derivat', 'type': 'string'},
                {'label': 'Cena', 'type': 'number'}
            ],
            'rows': []
        }

        #okrajsamo ime
        sprememba = db_zadnja_sprememba
        for i, j, k, l, m in zip(sprememba.drobnoProdajnaCena, sprememba.trosarina, const_marze, const_zrsbr, imena_derivatov):
            ddv = i - i / const_ddv
            vrednosti = [i-j-k-l-ddv, j, ddv, k, l]

            for n, o in zip(imena_postavk, vrednosti):
                json_torta['rows'].append(
                    {'c': [{'v': n}, {'v': m}, {'v': o}]}
                )

        """
        ['Postavka', 'znesek v EUR'],
        ['Ostalo', 13], ['Trosarina', 83], ['DDV', 1.4],
        ['Marza', 2.3], ['Clanarina', 46]
        """

        krneki = ""
        krneki_horiz = ""

        for a, b, c in zip(db_zadnja_sprememba.drobnoProdajnaCena, db_predzadnja_sprememba.drobnoProdajnaCena, imena_derivatov):
            znak = "&uarr; " if a - b > 0 else "&darr; "
            barva = "red;" if a - b > 0 else "lightgreen;"
            krneki += "\n" + c + ": " + str(a) + ' (<span style="color: ' + barva + '">' + znak + str(
                a - b) + "\xe2\x82\xac</span>) <br />"
            krneki_horiz += "\n" + '<li class="hor">' + c + ' (<span style="color: ' + barva + '">' + znak + str(
                a - b) + "\xe2\x82\xac</span>)" + '</li>'

        krneki = krneki.decode('UTF-8')
        krneki_horiz = krneki_horiz.decode('UTF-8')
        podatki2 = "['Derivat', 'Ostalo', 'Mar\xc5\xbea distributerjev', '\xc4\x8clanarina ZRSBR', 'Tro\xc5\xa1arina', 'DDV (" + str(
            (const_ddv - 1) * 100) + "%)'],"
        podatki2 = podatki2.decode('UTF-8')

        json_barchart = {
            'cols':
            [
                {'id': '', 'label': 'Derivat', 'type': 'string'},
                {'id': '', 'label': 'Ostalo', 'type': 'number'},
                {'id': '', 'label': 'Marza', 'type': 'number'},
                {'id': '', 'label': 'Clanarina', 'type': 'number'},
                {'id': '', 'label': 'Trosarina', 'type': 'number'},
                {'id': '', 'label': 'DDV', 'type': 'number'}
            ],
            'rows': []
        }

        #json_barchart['rows'].append({'c': [{'v': JSONdatum, 'f': 'null'}, {'v': str(i.temperatura), 'f': 'wtf'}, {'v': str(i.vlaga), 'f': 'wtf2'}]})



        for a, b, c, d, e in zip(db_zadnja_sprememba.drobnoProdajnaCena, db_zadnja_sprememba.trosarina, imena_derivatov, const_marze,
                                 const_zrsbr):
            ddv = a - a / const_ddv
            #               [derivat,   ostalo,             marža,          članarinaZRSBR, trošarina,      ddv          ]
            podatki2 += str(
                [c, round(a - b - d - e - ddv, 3), round(d, 3), round(e, 3), round(b, 3), round(ddv, 3)]) + ','
            json_barchart['rows'].append({'c': [{'v': c, 'f': c}, {'v': round(a - b - d - e - ddv, 3), 'f': str(round(a - b - d - e - ddv, 3))}, {'v': round(d, 3), 'f': str(round(d, 3))},{'v': round(e, 3), 'f': str(round(e, 3))},{'v': round(b, 3), 'f': str(round(b, 3))},{'v': round(ddv, 3), 'f': str(round(ddv, 3))}]})


        podatki2 = podatki2[:-1]

        podatki2 = '[' + podatki2 + ']'

        #self.response.out.write(podatki2)

        podatki = podatki2

        ##temperatura
        json_temperatura = {
            'cols':
            [
                {'id': '', 'label': 't', 'type': 'date'},
                {'id': '', 'label': 'T', 'type': 'number'},
                {'id': '', 'label': 'H', 'type': 'number'}
            ],
            'rows': []
        }

        temperatura = "['time', 'Temperatura', 'Vlaga'],\n"
        for i in db_cene:
            #temperatura = temperatura + "['" + str(i.date) + "', " + str(i.drobnoProdajnaCena[0]) + ", " + str(i.trosarina[0]) + "],\n"

            datum = datetime.strptime(str(i.date), '%Y-%m-%d %H:%M:%S.%f')

            JSONdatum = "Date(" + str(datum.year) + ", " + str(datum.month-1) + ", " + str(datum.day) + ", "
            JSONdatum += str(datum.hour) + ", " + str(datum.minute) + ", " + str(datum.second) + ")"


            json_temperatura['rows'].append({'c': [{'v': JSONdatum, 'f': 'null'}, {'v': str(i.drobnoProdajnaCena[0]), 'f': 'wtf'}, {'v': str(i.trosarina[0]), 'f': 'wtf2'}]})



        vrednost = []

        if len(db_tecaji_stari) > 0:
            for dan in db_tecaji_stari:
                vrednost.append(dan.tecaj_usd*dan.tecaj_rbob_gasoline)

            cena_prej = sum(vrednost)/float(len(vrednost))
            test_payload = "Cena v prejsnjem obdobju: " + str(cena_prej)

        if len(db_tecaji_aktualni) > 0:
            for dan in db_tecaji_aktualni:
                vrednost.append(dan.tecaj_usd*dan.tecaj_rbob_gasoline)

            test_payload += "\nCena v tekocem obdobju: " + str(sum(vrednost)/float(len(vrednost)))

        db_tecaji = ndbTecaj.query(ndbTecaj.date > db_timemark.date - timedelta(days=30)).fetch()

        test_payload += "\n<br />\n"
        for p in db_tecaji:

            datum = p.date.strftime('%Y-%m-%d %H:%M')
            vr = float(p.tecaj_rbob_gasoline)*float(p.tecaj_usd)
            rel = 100.0*float((vr - cena_prej)/cena_prej)

            if p.date >= db_timemark.date:
                test_payload += "<b>"
            test_payload += "[ " + datum + " | " + "{:10.2f}".format(vr) + " | " + "{:10.2f}".format(rel) + "% ]"

            if p.date >= db_timemark.date:
                test_payload += "</b>"

            test_payload += "<br />\n"


        template_values = {
            'zadnjaSprememba': db_zadnja_sprememba,
            'predZadnjaSprememba': db_predzadnja_sprememba,
            'podatki': podatki,
            'json_barchart': json_barchart,
            'krneki': krneki,
            'json_torta': json.dumps(json_torta),
            'subpage': subpage,
            'krneki_horiz': krneki_horiz,
            'temperatura': temperatura,
            'JSONtemperatura': json.dumps(json_temperatura),
            'datum': db_zadnja_sprememba.date,
            'payload': test_payload
        }

        template = jinja_environment.get_template('templates/neki.htm')
        self.response.out.write(template.render(template_values))


class Krneki(webapp2.RequestHandler):
    def get(self):
        self.response.out.write("google-site-verification: googled67ece29abf3e179.html")


class TecajiHandler(webapp2.RequestHandler):
    @staticmethod
    def get(self):
        try:
            page_1 = urllib2.urlopen(url_tecaj_usd).read()
            page_2 = urllib2.urlopen(url_tecaj_RBOB_gasoline).read()

            tecaj_usd = str(page_1).replace("><", ">\n<").split("\n")

            for i in tecaj_usd:
                if i.find("USD") > -1:
                    tecaj_usd = strip_tags(i)
                    break

            tecaj_rbob_gasoline = str(page_2).replace("tr><", "tr>\n<")
            tecaj_rbob_gasoline = tecaj_rbob_gasoline.replace("td><", "td>\n<").split("\n")

            for i in tecaj_rbob_gasoline:
                if i.find('<td class="text first"') > -1:
                    tecaj_rbob_gasoline = strip_tags(i)

            db_tecaj = ndbTecaj()
            db_tecaj.tecaj_usd = float(tecaj_usd)
            db_tecaj.tecaj_rbob_gasoline = float(tecaj_rbob_gasoline)
            db_tecaj.put()

        except urllib2.URLError, e:
            logging.error(e)


class TimeMarker(webapp2.RequestHandler):
    @staticmethod
    def get(self):

        #vsakic drugic posodobimo datum

        """

        @param self: test kaj je pa to
        """
        db_datum = ndbTimeMarker.query().fetch()[0]

        if not db_datum.odd:
            db_datum.odd = True
        else:
            db_datum.key.delete()
            db_datum = ndbTimeMarker()
            db_datum.odd = False

        db_datum.put()


class OsveziHandler(webapp2.RequestHandler):
    def get(self):
        try:
            result = urllib2.urlopen(url_poraba)
            result2 = []

            webCena = []
            webTros = []

            flag = False

            for i in result:
                if i.find('motorni bencin 95-oktanski') > -1:
                    flag = True
                elif i.find("Spremembe drobnoprodajnih cen naftnih derivatov v Sloveniji") > -1:
                    flag = False

                if flag:
                    result2.append(i)
            result2[0] = result2[0].replace("oktanski", "oktanski@")
            result2[0] = result2[0].replace(",", ".")
            result2[0] = result2[0].replace("</td>", ";</td>")
            result2[0] = result2[0].replace("gorivo", "gorivo@")
            result2[0] = result2[0].replace("Kurilno olje EL", "Kurilno olje EL@")
            a = strip_tags(result2[0]).split("@")

            #v a morajo biti na indeksih 1-4 vrstice z vsemi cenami
            #print a

            benz95 = a[1].split(";")
            benz98 = a[2].split(";")
            dizl = a[3].split(";")
            kurilc = a[4].split(";")

            webCena.append(round(float(benz95[6]), 3))
            webCena.append(round(float(benz98[6]), 3))
            webCena.append(round(float(dizl[6]), 3))
            webCena.append(round(float(kurilc[6]), 3))
            webTros.append(round(float(benz95[4]), 3))
            webTros.append(round(float(benz98[4]), 3))
            webTros.append(round(float(dizl[4]), 3))
            webTros.append(round(float(kurilc[4]), 3))

            db_sprememba_cene = ndbSpremembaCene.query_cene(None).fetch(1)

            db_cena = db_sprememba_cene[0].drobnoProdajnaCena
            db_tros = db_sprememba_cene[0].trosarina

            db_cena = [round(f, 3) for f in db_cena]
            db_tros = [round(f, 3) for f in db_tros]



            #presek dveh enakih mnozic je enak dolzini osnovne mnozice

            presekCen = set(db_cena).intersection(set(webCena))
            presekTros = set(db_tros).intersection(set(webTros))

            logging.info(db_cena)
            logging.info(webCena)

            if len(presekCen) < len(db_cena):
                #imamo spremembo cene
                dbNovaCena = ndbSpremembaCene()
                dbNovaCena.drobnoprodajna_cena = webCena
                dbNovaCena.trosarina = webTros
                dbNovaCena.put()

                mail.send_mail(sender="Naftni Poštar <postar@cenanafte.appspotmail.com>",
                               to="Miha Sedej <miha.sedej@gmail.com>",
                               subject="Sprememba cene naftnih derivatov",
                               body="""
Zdravo,

cena goriva se je spremenila!

http://cenanafte.appspot.com

LP

""")
                logging.info("Sprememba zaznana")
            else:
                logging.info("Sprememba ni zaznana")

        except urllib2.URLError, e:
            self.response.out.write(e)


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

#URL ruter
app = webapp2.WSGIApplication([('/osvezi', OsveziHandler),
                               ('/tecaji', TecajiHandler),
                               ('/init', InitHandler),
                               ('/', IndexHandler),
                               ('/oblikovanje', IndexHandler),
                               ('/podrobno', IndexHandler),
                               ('/casovno', IndexHandler),
                               ('/naroci', IndexHandler),
                               ('/napoved', IndexHandler),
                               ('/timemarker', TimeMarker),
                               ('/googled67ece29abf3e179.html', Krneki)],
                              debug=True)