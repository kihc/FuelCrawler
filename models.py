__author__ = 'Miha'

from google.appengine.ext import ndb


class NdbSpremembaCene(ndb.Model):
    #cene v cetvorckih - 95, 98, diesel, kurilno
    drobnoprodajna_cena = ndb.FloatProperty(repeated=True)
    trosarina = ndb.FloatProperty(repeated=True)
    date = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def query_cene(cls, ancestor_key):
        return cls.query(ancestor=ancestor_key).order(-cls.date)


class NdbTecaj(ndb.Model):
    tecaj_usd = ndb.FloatProperty()
    tecaj_rbob_gasoline = ndb.FloatProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def query_tecaj(cls, ancestor_key):
        return cls.query(ancestor=ancestor_key).order(-cls.date)


class NdbTimeMarker(ndb.Model):
    odd = ndb.BooleanProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)