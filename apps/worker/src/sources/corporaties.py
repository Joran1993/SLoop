"""Statische mapping van gemeente → woningcorporatie(s).

Gebaseerd op het publieke register van de Autoriteit Woningcorporaties (AW)
en het Aedes ledenbestand. Dekt de ~150 gemeenten met de meeste sloopactiviteit.

Gebruik:
    from src.sources.corporaties import get_corporaties_for_gemeente
    names = get_corporaties_for_gemeente("Amsterdam")
    # → ["Ymere", "Eigen Haard", "Rochdale", "De Alliantie", "Lieven de Key"]
"""
from __future__ import annotations

# Gemeente (lowercase, gestript) → lijst van corporaties (op relevantie/marktaandeel)
_CORPORATIES: dict[str, list[str]] = {
    # Noord-Holland
    "amsterdam": ["Ymere", "Eigen Haard", "Rochdale", "De Alliantie", "Lieven de Key", "Stadgenoot"],
    "haarlem": ["Ymere", "Elan Wonen", "Pré Wonen"],
    "zaanstad": ["Parteon", "Ymere"],
    "haarlemmermeer": ["Ymere", "De Alliantie"],
    "almere": ["De Alliantie", "Ymere"],
    "amsterdam-zuidoost": ["Ymere", "Rochdale", "De Alliantie"],
    "alkmaar": ["Woonwaard"],
    "hoorn": ["IntermarisHoeksteen", "WoonCompagnie"],
    "den helder": ["Woontij", "WoonCompagnie"],
    "purmerend": ["Wooncompagnie"],
    "hilversum": ["Dudok Wonen"],
    "amstelveen": ["Eigen Haard"],
    "diemen": ["Ymere"],
    "heerhugowaard": ["Woonwaard"],
    "castricum": ["Kennemer Wonen"],
    "langedijk": ["Woonwaard"],
    "heiloo": ["Kennemer Wonen"],
    "enkhuizen": ["IntermarisHoeksteen"],
    "schagen": ["WoonCompagnie"],
    "texel": ["Woontij"],

    # Zuid-Holland
    "rotterdam": ["Vestia", "Havensteder", "Woonbron", "Ressort Wonen"],
    "den haag": ["Vestia", "Haag Wonen", "Staedion", "Vidomes"],
    "leiden": ["Portaal", "Ons Doel", "Ymere"],
    "dordrecht": ["Trivire", "Woonbron"],
    "delft": ["Vestia", "Woonbron", "Vidomes"],
    "zoetermeer": ["Vestia", "WoonInvest"],
    "gouda": ["Woonpartners Midden-Holland", "Mozaïek Wonen"],
    "westland": ["Wonen Wateringen"],
    "alphen aan den rijn": ["Woonforte"],
    "schiedam": ["Woonplus Schiedam"],
    "vlaardingen": ["Waterweg Wonen"],
    "spijkenisse": ["Woonkoepel Voorne Putten Rozenburg"],
    "ridderkerk": ["Woonbron"],
    "capelle aan den ijssel": ["Havensteder"],
    "krimpen aan den ijssel": ["Havensteder"],
    "barendrecht": ["Woonbron"],
    "hellevoetsluis": ["Woonkoepel Voorne Putten Rozenburg"],
    "pijnacker-nootdorp": ["Vidomes"],
    "leidschendam-voorburg": ["Vidomes", "Vestia"],
    "rijswijk": ["Haag Wonen"],
    "wassenaar": ["Haag Wonen"],
    "bodegraven-reeuwijk": ["Woonforte"],

    # Utrecht
    "utrecht": ["Bo-Ex", "Mitros", "Portaal", "SSH"],
    "amersfoort": ["De Alliantie", "Portaal", "Ymere"],
    "nieuwegein": ["Bo-Ex", "Mitros"],
    "veenendaal": ["Vallei Wonen"],
    "zeist": ["RK Woningbouwvereniging Zeist"],
    "soest": ["Portaal"],
    "woerden": ["Corporatie De Woonplaats"],
    "houten": ["Mitros"],
    "de bilt": ["De Alliantie"],
    "stichtse vecht": ["WoonAlliantie Stichtse Vecht"],

    # Noord-Brabant
    "eindhoven": ["Woonbedrijf", "Trudo", "Area"],
    "tilburg": ["TBV Wonen", "Tiwos", "WonenBreburg"],
    "breda": ["AlleeWonen", "Laurentius", "WonenBreburg"],
    "s-hertogenbosch": ["BrabantWonen", "Zayaz"],
    "helmond": ["Woonbedrijf", "Compaen"],
    "oss": ["Mooiland"],
    "bergen op zoom": ["l'escaut"],
    "roosendaal": ["AlleeWonen"],
    "veghel": ["BrabantWonen"],
    "veldhoven": ["Woonbedrijf"],
    "best": ["Woonbedrijf"],
    "waalwijk": ["Casade"],
    "dongen": ["Casade"],
    "geertruidenberg": ["WonenBreburg"],
    "oosterhout": ["AlleeWonen", "WonenBreburg"],
    "etten-leur": ["AlleeWonen"],
    "goes": ["Woongoed Goes"],
    "meierijstad": ["BrabantWonen"],
    "boxtel": ["Joost Wonen"],

    # Gelderland
    "arnhem": ["Portaal", "Volkshuisvesting Arnhem", "Vivare"],
    "nijmegen": ["Portaal", "Talis", "Woonwaarts"],
    "apeldoorn": ["Ons Huis", "Triada"],
    "ede": ["Woonstede", "Veste"],
    "doetinchem": ["ProWonen"],
    "zutphen": ["Woonbedrijf Ieder1"],
    "harderwijk": ["Uwoon"],
    "wageningen": ["Idealis", "Portaal"],
    "winterswijk": ["ProWonen"],
    "montferland": ["ProWonen"],
    "aalten": ["ProWonen"],
    "buren": ["Rivierenland"],
    "tiel": ["Rivierenland"],
    "nijkerk": ["Uwoon"],
    "barneveld": ["Woningstichting Barneveld"],
    "rheden": ["Vivare"],

    # Overijssel
    "enschede": ["Domijn", "De Woonplaats", "Ons Stroom"],
    "zwolle": ["SWZ", "deltaWonen", "WBO Wonen"],
    "deventer": ["Rentree", "Ieder1"],
    "almelo": ["De Woonplaats", "Beter Wonen Vechtdal"],
    "hengelo": ["Welbions"],
    "oldenzaal": ["Domijn"],
    "hardenberg": ["WBO Wonen"],
    "steenwijk": ["WBO Wonen"],
    "kampen": ["deltaWonen"],

    # Groningen
    "groningen": ["Nijestee", "Lefier", "De Huismeesters"],
    "emmen": ["Domesta", "Lefier"],
    "stadskanaal": ["Lefier"],
    "veendam": ["Lefier"],
    "hoogezand-sappemeer": ["Lefier"],
    "delfzijl": ["Acantus"],
    "appingedam": ["Acantus"],
    "oldambt": ["Acantus"],

    # Friesland
    "leeuwarden": ["Elkien", "Accolade", "WoonFriesland"],
    "smallingerland": ["Accolade"],
    "heerenveen": ["Accolade"],
    "súdwest-fryslân": ["WoonFriesland"],
    "de friese meren": ["WoonFriesland"],

    # Drenthe
    "assen": ["Actium"],
    "meppel": ["Triada", "WBO Wonen"],
    "hoogeveen": ["Actium"],
    "coevorden": ["Domesta"],

    # Limburg
    "maastricht": ["Maasvallei", "Woonpunt"],
    "sittard-geleen": ["Wonen Zuid", "Maasvallei"],
    "heerlen": ["Weller", "Wonen Zuid"],
    "venlo": ["Wonen Limburg", "Antares"],
    "roermond": ["Wonen Limburg"],
    "weert": ["Wonen Limburg"],
    "venray": ["Wonen Limburg"],
    "brunssum": ["Weller"],
    "kerkrade": ["Weller"],
    "landgraaf": ["Weller"],
    "nuth": ["Wonen Zuid"],
    "echt-susteren": ["Wonen Limburg"],
    "maasgouw": ["Wonen Limburg"],

    # Zeeland
    "middelburg": ["Zeeuwland"],
    "vlissingen": ["Zeeuwland"],
    "goes": ["Woongoed Zeeuws-Vlaanderen"],
    "terneuzen": ["Woongoed Zeeuws-Vlaanderen"],

    # Flevoland
    "lelystad": ["Centrada"],
    "dronten": ["Mercatus"],
    "urk": ["Beter Wonen"],
    "noordoostpolder": ["Mercatus"],
    "zeewolde": ["De Alliantie"],

    # Flevoland / Almere al hierboven

    # Gelderland (extra)
    "berg en dal": ["Talis", "Woonwaarts"],
    "bronckhorst": ["ProWonen"],
    "zevenaar": ["Plavei"],
    "wijchen": ["Talis", "Woonwaarts"],
    "oude ijsselstreek": ["ProWonen"],
    "heumen": ["Talis"],
    "beuningen": ["Talis", "Woonwaarts"],
    "druten": ["Talis", "Woonwaarts"],
    "brummen": ["Vivare"],
    "oost gelre": ["ProWonen"],
    "duiven": ["Plavei"],
    "westervoort": ["Plavei"],
    "voorst": ["Triada"],

    # Overijssel (extra)
    "rijssen-holten": ["Reggewoon"],
    "zwartewaterland": ["deltaWonen"],

    # Groningen (extra)
    "westerkwartier": ["Lefier"],

    # Drenthe (extra)
    "tynaarlo": ["Actium"],

    # Noord-Holland (extra)
    "huizen": ["De Alliantie"],
    "koggenland": ["WoonCompagnie"],
    "heemskerk": ["Kennemer Wonen", "Pré Wonen"],

    # Utrecht (extra)
    "woudenberg": ["Vallei Wonen"],
    "nieuwkoop": ["Woonforte"],

    # Zeeland (extra)
    "hulst": ["Woongoed Zeeuws-Vlaanderen"],
    "sluis": ["Woongoed Zeeuws-Vlaanderen"],

    # Noord-Brabant (extra)
    "asten": ["Area"],
    "hilvarenbeek": ["Casade"],
    "land van cuijk": ["Mooiland"],
    "gennep": ["Mooiland"],

    # Gelderland (Nijmegen omgeving extra)
    "nunspeet": ["Uwoon"],

    # Limburg (extra)
    "bergen (l)": ["Wonen Limburg"],
}


# Corporatienaam → contactgegevens (publiek beschikbaar op corporatie-websites)
_CONTACT: dict[str, dict] = {
    "Ymere":                    {"website": "https://www.ymere.nl",               "telefoon": "088 – 000 00 00"},
    "Eigen Haard":              {"website": "https://www.eigenhaard.nl",           "telefoon": "020 – 517 79 00"},
    "Rochdale":                 {"website": "https://www.rochdale.nl",             "telefoon": "020 – 408 60 00"},
    "De Alliantie":             {"website": "https://www.de-alliantie.nl",         "telefoon": "088 – 828 28 28"},
    "Lieven de Key":            {"website": "https://www.dekey.nl",                "telefoon": "020 – 520 98 00"},
    "Stadgenoot":               {"website": "https://www.stadgenoot.nl",           "telefoon": "020 – 251 68 00"},
    "Elan Wonen":               {"website": "https://www.elanwonen.nl",            "telefoon": "023 – 515 72 00"},
    "Pré Wonen":                {"website": "https://www.prewonen.nl",             "telefoon": "088 – 537 99 11"},
    "Parteon":                  {"website": "https://www.parteon.nl",              "telefoon": "075 – 615 49 33"},
    "Woonwaard":                {"website": "https://www.woonwaard.nl",            "telefoon": "072 – 514 07 40"},
    "WoonCompagnie":            {"website": "https://www.wooncompagnie.nl",        "telefoon": "0299 – 476 400"},
    "IntermarisHoeksteen":      {"website": "https://www.intermarishoeksteen.nl",  "telefoon": "0229 – 277 777"},
    "Woontij":                  {"website": "https://www.woontij.nl",              "telefoon": "0223 – 671 000"},
    "Kennemer Wonen":           {"website": "https://www.kennemerwonen.nl",        "telefoon": "0251 – 258 888"},
    "Dudok Wonen":              {"website": "https://www.dudokwonen.nl",           "telefoon": "035 – 528 07 00"},
    "Vestia":                   {"website": "https://www.vestia.nl",               "telefoon": "088 – 800 08 00"},
    "Havensteder":              {"website": "https://www.havensteder.nl",          "telefoon": "010 – 200 36 00"},
    "Woonbron":                 {"website": "https://www.woonbron.nl",             "telefoon": "088 – 226 00 00"},
    "Haag Wonen":               {"website": "https://www.haagwonen.nl",            "telefoon": "070 – 353 44 44"},
    "Staedion":                 {"website": "https://www.staedion.nl",             "telefoon": "070 – 329 32 93"},
    "Portaal":                  {"website": "https://www.portaal.nl",              "telefoon": "088 – 800 08 00"},
    "Ons Doel":                 {"website": "https://www.onsdoel.nl",              "telefoon": "071 – 516 40 00"},
    "Vidomes":                  {"website": "https://www.vidomes.nl",              "telefoon": "015 – 251 36 00"},
    "WoonInvest":               {"website": "https://www.wooninvest.nl",           "telefoon": "079 – 368 20 00"},
    "Trivire":                  {"website": "https://www.trivire.nl",              "telefoon": "078 – 639 18 00"},
    "Woonplus Schiedam":        {"website": "https://www.woonplus.nl",             "telefoon": "010 – 246 10 00"},
    "Waterweg Wonen":           {"website": "https://www.waterweg-wonen.nl",       "telefoon": "010 – 434 18 88"},
    "Woonforte":                {"website": "https://www.woonforte.nl",            "telefoon": "0172 – 580 300"},
    "Mozaïek Wonen":            {"website": "https://www.mozaiekwonen.nl",         "telefoon": "0182 – 398 500"},
    "Bo-Ex":                    {"website": "https://www.bo-ex.nl",                "telefoon": "030 – 687 55 00"},
    "Mitros":                   {"website": "https://www.portaal.nl",              "telefoon": "088 – 800 08 00"},
    "SSH":                      {"website": "https://www.sshxl.nl",               "telefoon": "030 – 231 15 11"},
    "Vallei Wonen":             {"website": "https://www.valleiwonen.nl",          "telefoon": "0318 – 524 100"},
    "TBV Wonen":                {"website": "https://www.tbvwonen.nl",             "telefoon": "013 – 594 38 00"},
    "Tiwos":                    {"website": "https://www.tiwos.nl",                "telefoon": "013 – 583 83 83"},
    "WonenBreburg":             {"website": "https://www.wonenbreburg.nl",         "telefoon": "013 – 462 71 71"},
    "AlleeWonen":               {"website": "https://www.alleewonen.nl",           "telefoon": "076 – 548 19 00"},
    "Laurentius":               {"website": "https://www.laurentius.nl",           "telefoon": "076 – 523 82 00"},
    "BrabantWonen":             {"website": "https://www.brabantwonen.nl",         "telefoon": "073 – 621 10 21"},
    "Zayaz":                    {"website": "https://www.zayaz.nl",                "telefoon": "073 – 687 87 00"},
    "Woonbedrijf":              {"website": "https://www.woonbedrijf.com",         "telefoon": "040 – 265 99 99"},
    "Trudo":                    {"website": "https://www.trudo.nl",                "telefoon": "040 – 235 00 00"},
    "Area":                     {"website": "https://www.area.nl",                 "telefoon": "0492 – 508 508"},
    "Compaen":                  {"website": "https://www.compaen.nl",              "telefoon": "0492 – 548 900"},
    "Casade":                   {"website": "https://www.casade.nl",               "telefoon": "0416 – 375 400"},
    "Mooiland":                 {"website": "https://www.mooiland.nl",             "telefoon": "0412 – 637 600"},
    "Nijestee":                 {"website": "https://www.nijestee.nl",             "telefoon": "050 – 368 36 83"},
    "Lefier":                   {"website": "https://www.lefier.nl",               "telefoon": "088 – 064 00 00"},
    "De Huismeesters":          {"website": "https://www.dehuismeesters.nl",       "telefoon": "050 – 520 03 00"},
    "Acantus":                  {"website": "https://www.acantus.nl",              "telefoon": "0596 – 636 000"},
    "Domesta":                  {"website": "https://www.domesta.nl",              "telefoon": "0591 – 617 300"},
    "Elkien":                   {"website": "https://www.elkien.nl",               "telefoon": "058 – 233 00 00"},
    "Accolade":                 {"website": "https://www.accolade.nl",             "telefoon": "0513 – 489 000"},
    "WoonFriesland":            {"website": "https://www.woonfriesland.nl",        "telefoon": "0512 – 358 300"},
    "Actium":                   {"website": "https://www.actium.nl",               "telefoon": "0592 – 398 800"},
    "Maasvallei":               {"website": "https://www.maasvallei.nl",           "telefoon": "043 – 351 97 60"},
    "Woonpunt":                 {"website": "https://www.woonpunt.nl",             "telefoon": "043 – 322 50 20"},
    "Wonen Zuid":               {"website": "https://www.wonenzuid.nl",            "telefoon": "045 – 579 79 79"},
    "Weller":                   {"website": "https://www.weller.nl",               "telefoon": "045 – 560 10 00"},
    "Wonen Limburg":            {"website": "https://www.wonenlimburg.nl",         "telefoon": "077 – 359 80 00"},
    "Antares":                  {"website": "https://www.antaresnet.nl",           "telefoon": "077 – 320 02 00"},
    "Domijn":                   {"website": "https://www.domijn.nl",               "telefoon": "053 – 484 84 84"},
    "De Woonplaats":            {"website": "https://www.dewoonplaats.nl",         "telefoon": "053 – 435 34 00"},
    "Welbions":                 {"website": "https://www.welbions.nl",             "telefoon": "074 – 245 06 00"},
    "SWZ":                      {"website": "https://www.swz.nl",                  "telefoon": "038 – 455 44 55"},
    "deltaWonen":               {"website": "https://www.deltawonen.nl",           "telefoon": "038 – 339 11 00"},
    "WBO Wonen":                {"website": "https://www.wbowonen.nl",             "telefoon": "0523 – 261 200"},
    "Rentree":                  {"website": "https://www.rentree.nl",              "telefoon": "0570 – 501 200"},
    "Ieder1":                   {"website": "https://www.ieder1.nl",               "telefoon": "0575 – 597 700"},
    "ProWonen":                 {"website": "https://www.prowonen.nl",             "telefoon": "0315 – 285 285"},
    "Talis":                    {"website": "https://www.talis.nl",                "telefoon": "024 – 359 13 91"},
    "Woonwaarts":               {"website": "https://www.woonwaarts.nl",           "telefoon": "024 – 399 96 00"},
    "Vivare":                   {"website": "https://www.vivare.nl",               "telefoon": "026 – 377 97 79"},
    "Volkshuisvesting Arnhem":  {"website": "https://www.volkshuisvestingarnhem.nl","telefoon": "026 – 377 87 00"},
    "Ons Huis":                 {"website": "https://www.onshuis.com",             "telefoon": "055 – 579 78 00"},
    "Triada":                   {"website": "https://www.triada.nl",               "telefoon": "0578 – 699 300"},
    "Woonstede":                {"website": "https://www.woonstede.nl",            "telefoon": "0318 – 594 777"},
    "Uwoon":                    {"website": "https://www.uwoon.nl",                "telefoon": "0341 – 491 888"},
    "Plavei":                   {"website": "https://www.plavei.nl",               "telefoon": "0316 – 283 900"},
    "Reggewoon":                {"website": "https://www.reggewoon.nl",            "telefoon": "0548 – 545 300"},
    "Centrada":                 {"website": "https://www.centrada.nl",             "telefoon": "0320 – 261 800"},
    "Mercatus":                 {"website": "https://www.mercatus.nl",             "telefoon": "0321 – 380 300"},
    "Zeeuwland":                {"website": "https://www.zeeuwland.nl",            "telefoon": "0118 – 680 680"},
    "Woongoed Zeeuws-Vlaanderen": {"website": "https://www.woongoedzv.nl",         "telefoon": "0115 – 649 200"},
    "Woningstichting Barneveld": {"website": "https://www.wsbarneveld.nl",         "telefoon": "0342 – 414 400"},
    "l'escaut":                 {"website": "https://www.lescaut.nl",              "telefoon": "0164 – 278 900"},
}


def get_corporatie_contact(naam: str | None) -> dict:
    """Geeft contactgegevens voor een corporatienaam, met DB-kolomnamen als keys."""
    if not naam:
        return {}
    raw = _CONTACT.get(naam, {})
    if not raw:
        return {}
    return {
        "contact_website":  raw.get("website"),
        "contact_telefoon": raw.get("telefoon"),
    }


def get_corporaties_for_gemeente(gemeente: str | None) -> list[str]:
    """Geeft de bekende woningcorporatie(s) voor een gemeente terug.

    Probeert exact, dan gestript/lowercase match.
    Geeft lege lijst als de gemeente onbekend is.
    """
    if not gemeente:
        return []
    key = gemeente.strip().lower()
    # Directe match
    if key in _CORPORATIES:
        return _CORPORATIES[key]
    # Probeer zonder streepjes en komma's
    normalized = key.replace("-", " ").split(",")[0].strip()
    return _CORPORATIES.get(normalized, [])


def get_primary_corporatie(gemeente: str | None) -> str | None:
    """Geeft de meest waarschijnlijke corporatie (eerste in de lijst) of None."""
    corps = get_corporaties_for_gemeente(gemeente)
    return corps[0] if corps else None
