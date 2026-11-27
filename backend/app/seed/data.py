"""Sample data taken from the Figma Make prototype (src/data.ts).

Everything here is illustrative: subjects are anonymous ("Subjekt A") and
documents are marked as samples ("ukážka"). Not for production.
"""

SUBJECTS = [
    {"slug": "subjekt-a", "name": "Subjekt A", "short_name": "A"},
    {"slug": "subjekt-b", "name": "Subjekt B", "short_name": "B"},
    {"slug": "subjekt-c", "name": "Subjekt C", "short_name": "C"},
]

CATEGORIES = [
    {"slug": "zdravotnictvo", "label": "Zdravotníctvo", "tagline": "Lekári a nemocnice"},
    {"slug": "skolstvo", "label": "Školstvo", "tagline": "Školy a vzdelávanie"},
    {"slug": "doprava", "label": "Doprava", "tagline": "Cesty, vlaky, MHD"},
    {"slug": "sprava", "label": "Verejná správa", "tagline": "Úrady a služby"},
]

# Source documents for verdicts, one per promise type (all samples).
EVIDENCE_DOCUMENTS = {
    "konkretny": {"kind": "rozpocet", "title": "Štátny rozpočet (ukážka)"},
    "zakon": {"kind": "zakon", "title": "Zbierka zákonov (ukážka)"},
    "stavba": {"kind": "zmluva", "title": "Zmluva o dielo (ukážka)"},
    "vagny": {"kind": "uznesenie", "title": "Uznesenie vlády (ukážka)"},
}

# verdict: (value, explanation); history: older published versions, oldest first.
PROMISES = [
    {
        "slug": "skoly",
        "title": "Podporíme modernizáciu školských učební",
        "quote": "Podporíme modernizáciu školských učební a digitálne vybavenie škôl.",
        "subject": "subjekt-b",
        "category": "skolstvo",
        "type": "konkretny",
        "verdict": (
            "splnene",
            "Dôkazy potvrdzujú, že sa to naozaj stalo. Peniaze boli v štátnom rozpočte.",
        ),
    },
    {
        "slug": "zdravie",
        "title": "Zvýšime dostupnosť všeobecnej zdravotnej starostlivosti",
        "quote": "Zvýšime dostupnosť všeobecnej zdravotnej starostlivosti v regiónoch.",
        "subject": "subjekt-a",
        "category": "zdravotnictvo",
        "type": "zakon",
        "verdict": ("ciastocne", "Návrh zákona je v parlamente, ale ešte nie je schválený."),
    },
    {
        "slug": "doprava",
        "title": "Pripravíme verejný plán modernizácie dopravnej infraštruktúry",
        "quote": "Pripravíme verejný plán modernizácie dopravnej infraštruktúry.",
        "subject": "subjekt-a",
        "category": "doprava",
        "type": "konkretny",
        "verdict": ("ciastocne", "Plán sa pripravuje, zatiaľ je hotová len jeho časť."),
    },
    {
        "slug": "sluzby",
        "title": "Zlepšíme kvalitu verejných služieb",
        "quote": "Zlepšíme kvalitu verejných služieb.",
        "subject": "subjekt-c",
        "category": "sprava",
        "type": "vagny",
        "verdict": ("nesplnene", "Žiadne merateľné zlepšenie sa nepodarilo preukázať."),
    },
    {
        "slug": "obchvat",
        "title": "Postavíme obchvat mesta do konca volebného obdobia",
        "quote": "Do konca volebného obdobia postavíme nový obchvat mesta.",
        "subject": "subjekt-b",
        "category": "doprava",
        "type": "stavba",
        "verdict": (
            "nesplnene",
            "Termín uplynul a stavba sa nezačala. Verejné obstarávanie zrušili.",
        ),
        "history": [("ciastocne", "Prebieha verejné obstarávanie na zhotoviteľa stavby.")],
    },
    {
        "slug": "ambulancie",
        "title": "Otvoríme nové ambulancie v každom okrese",
        "quote": "V každom okrese otvoríme novú ambulanciu všeobecného lekára.",
        "subject": "subjekt-c",
        "category": "zdravotnictvo",
        "type": "konkretny",
        "verdict": (
            "nesplnene",
            "Ambulancie sa neotvorili. Rozhodujú o nich kraje, nie je to v kompetencii strany.",
        ),
    },
    {
        "slug": "platy-ucitelov",
        "title": "Zvýšime platy učiteľov o 10 %",
        "quote": "Od budúceho roka zvýšime platy učiteľov o 10 percent.",
        "subject": "subjekt-a",
        "category": "skolstvo",
        "type": "zakon",
        "verdict": ("splnene", "Zvýšenie schválila vláda a platí od januára."),
    },
    {
        "slug": "vlaky",
        "title": "Vlaky v regiónoch budú chodiť každú hodinu",
        "quote": "Zavedieme pravidelné spoje, aby vlaky v regiónoch chodili každú hodinu.",
        "subject": "subjekt-c",
        "category": "doprava",
        "type": "konkretny",
        "verdict": ("splnene", "Od decembra chodia vlaky v regiónoch každú hodinu."),
    },
    {
        "slug": "cyklotrasy",
        "title": "Vybudujeme 200 km nových cyklotrás",
        "quote": (
            "Vybudujeme 200 kilometrov nových cyklotrás a zlepšíme infraštruktúru pre cyklistov."
        ),
        "subject": "subjekt-a",
        "category": "doprava",
        "type": "stavba",
        "verdict": ("ciastocne", "Postavili zatiaľ asi 80 km, práce pokračujú."),
    },
    {
        "slug": "skolky",
        "title": "Každé dieťa dostane miesto v škôlke",
        "quote": "Zabezpečíme miesto v materskej škole pre každé dieťa od troch rokov.",
        "subject": "subjekt-c",
        "category": "skolstvo",
        "type": "konkretny",
        "verdict": (
            "ciastocne",
            "Pribudli nové miesta, ale peniaze v rozpočte zatiaľ nestačia pre všetky deti.",
        ),
    },
    {
        "slug": "online-urad",
        "title": "Všetko na úrade vybavíš online",
        "quote": "Digitalizácia umožní vybaviť všetky úradné služby online, bez čakania.",
        "subject": "subjekt-b",
        "category": "sprava",
        "type": "konkretny",
        "verdict": ("ciastocne", "Online funguje zatiaľ asi tretina služieb."),
    },
    {
        "slug": "byrokracia",
        "title": "Znížime byrokraciu pre ľudí aj firmy",
        "quote": "Znížime byrokraciu a zjednodušíme život ľuďom aj firmám.",
        "subject": "subjekt-a",
        "category": "sprava",
        "type": "vagny",
        "verdict": ("nesplnene", "Úrady fungujú rovnako ako predtým, sľúbená zmena neprišla."),
    },
    {
        "slug": "cakacie-lehoty",
        "title": "Skrátime čakanie na operácie na polovicu",
        "quote": "Skrátime čakacie lehoty na plánované operácie na polovicu.",
        "subject": "subjekt-b",
        "category": "zdravotnictvo",
        "type": "konkretny",
        "verdict": ("splnene", "Čakanie na plánované operácie sa skrátilo na polovicu."),
    },
    {
        "slug": "nemocnica",
        "title": "Postavíme novú nemocnicu v krajskom meste",
        "quote": "Postavíme novú modernú nemocnicu v krajskom meste.",
        "subject": "subjekt-a",
        "category": "zdravotnictvo",
        "type": "stavba",
        "verdict": ("ciastocne", "Verejné obstarávanie na stavbu prebieha."),
    },
    {
        "slug": "ucebnice",
        "title": "Učebnice budú pre žiakov zadarmo",
        "quote": "Prijmeme zákon, vďaka ktorému budú učebnice pre všetkých žiakov zadarmo.",
        "subject": "subjekt-b",
        "category": "skolstvo",
        "type": "zakon",
        "verdict": ("splnene", "Parlament zákon schválil a učebnice sú zadarmo."),
    },
    {
        "slug": "miestne-dane",
        "title": "Znížime miestne dane v obciach",
        "quote": "Znížime miestne dane, ktoré platia ľudia v obciach.",
        "subject": "subjekt-c",
        "category": "sprava",
        "type": "zakon",
        "verdict": (
            "nesplnene",
            "Dane sa neznížili. Rozhoduje o nich samospráva, nie parlament.",
        ),
    },
]


def _wiki(slug: str) -> str:
    return f"https://sk.wikipedia.org/wiki/{slug}"


_L = r"\p{L}*"  # any letters, used inside stems

GLOSSARY = [
    {
        "name": "Parlament",
        "short": "Zastupuje občanov a prijíma zákony.",
        "long": (
            "Najvyšší zastupiteľský a zákonodarný orgán štátu. Reprezentuje občanov a prijíma "
            "zákony, ktoré platia v danej krajine."
        ),
        "example": "Na Slovensku je to Národná rada SR.",
        "wiki_url": _wiki("Parlament"),
        "stems": ["parlament"],
    },
    {
        "name": "Legislatíva",
        "short": "Zákony a pravidlá, podľa ktorých funguje štát.",
        "long": "Súhrn zákonov a ďalších právnych predpisov aj postup, ako vznikajú.",
        "example": "Na splnenie sľubu môže byť potrebná zmena zákona.",
        "wiki_url": _wiki("Legislatíva"),
        "stems": ["legislatív"],
    },
    {
        "name": "Štátny rozpočet",
        "short": "Plán štátnych príjmov a výdavkov.",
        "long": "Plán, koľko peňazí štát v danom roku čaká a na čo ich minie.",
        "example": "Investičný sľub potrebuje peniaze vyčlenené v rozpočte.",
        "wiki_url": _wiki("Štátny_rozpočet"),
        "stems": [f"štátn{_L} rozpoč", "rozpoč"],
    },
    {
        "name": "Kompetencia",
        "short": "Právomoc rozhodovať o určitej veci.",
        "long": "Rozsah právomocí, úloh a zodpovednosti osoby alebo orgánu.",
        "example": "Ak niečo nie je v kompetencii úradu, nemôže o tom rozhodnúť.",
        "wiki_url": _wiki("Kompetencia"),
        "stems": ["kompeten"],
    },
    {
        "name": "Vláda",
        "short": "Riadi štát a vykonáva zákony.",
        "example": "Napríklad pripravuje návrh štátneho rozpočtu.",
        "wiki_url": _wiki("Vláda"),
        "stems": ["vlád"],
    },
    {
        "name": "Koalícia",
        "short": "Strany, ktoré spolupracujú a podporujú vládu.",
        "example": "Koaličné strany sa dohodnú na spoločnom programe.",
        "wiki_url": _wiki("Koalícia"),
        "stems": ["koalíci", "koaličn"],
    },
    {
        "name": "Opozícia",
        "short": "Strany, ktoré nie sú súčasťou vládnej koalície.",
        "example": "Opozícia kontroluje vládu a navrhuje zmeny.",
        "wiki_url": _wiki("Opozícia_(politika)"),
        "stems": ["opozíci", "opozičn"],
    },
    {
        "name": "Poslanec",
        "short": "Zvolený zástupca občanov.",
        "example": "Poslanci rokujú o návrhoch a hlasujú o nich.",
        "wiki_url": _wiki("Poslanec"),
        "stems": ["poslan(?:ec|ci|ca|cov|com|covi|kyň)"],
    },
    {
        "name": "Verdikt",
        "short": "Výsledok overenia sľubu.",
        "example": "Napríklad „Splnený“ alebo „Čiastočne splnený“.",
        "wiki_url": _wiki("Verdikt"),
        "stems": ["verdikt"],
    },
    {
        "name": "Dôkaz",
        "short": "Dokument alebo údaj, o ktorý sa opiera hodnotenie.",
        "example": "Môže to byť zákon, uznesenie alebo úradný záznam.",
        "wiki_url": _wiki("Dôkaz"),
        "stems": ["dôkaz"],
    },
    {
        "name": "Verejné obstarávanie",
        "short": "Ako úrady nakupujú tovary a služby.",
        "example": "Napríklad výber firmy na opravu verejnej budovy.",
        "wiki_url": _wiki("Verejné_obstarávanie"),
        "stems": [f"verejn{_L} obstarávan"],
    },
    {
        "name": "Ústava",
        "short": "Najvyšší zákon štátu a práva občanov.",
        "example": "Určuje napríklad právomoci štátnych orgánov.",
        "wiki_url": _wiki("Ústava"),
        "stems": ["ústav(?:a|y|e|u|ou|n)"],
    },
    {
        "name": "Zákon",
        "short": "Pravidlo, ktoré schválil parlament a platí pre všetkých.",
        "example": "Napríklad zákon o bezplatných učebniciach.",
        "wiki_url": _wiki("Zákon_(právo)"),
        "stems": ["zákon(?!odar)"],
    },
    {
        "name": "Región",
        "short": "Časť krajiny, napríklad kraj alebo okres.",
        "example": "Sľub „v regiónoch“ znamená mimo veľkých miest.",
        "wiki_url": _wiki("Región"),
        "stems": ["regió", "región"],
    },
    {
        "name": "Samospráva",
        "short": "Obce, mestá a kraje, ktoré rozhodujú o svojich veciach.",
        "example": "Miestne dane určuje obec, nie vláda.",
        "wiki_url": _wiki("Samospráva"),
        "stems": ["samospráv"],
    },
    {
        "name": "Infraštruktúra",
        "short": "Cesty, železnice, siete a iné veci, ktoré používame všetci.",
        "example": "Diaľnice, mosty alebo cyklotrasy.",
        "wiki_url": _wiki("Infraštruktúra"),
        "stems": ["infraštruktúr"],
    },
    {
        "name": "Volebné obdobie",
        "short": "Čas medzi dvoma voľbami, zvyčajne 4 roky.",
        "example": "Sľub „do konca volebného obdobia“ má jasný termín.",
        "wiki_url": _wiki("Volebné_obdobie"),
        "stems": [f"volebn{_L} obdob"],
    },
    {
        "name": "Verejné služby",
        "short": "Služby, ktoré pre ľudí zabezpečuje štát alebo obec.",
        "example": "Napríklad vydanie občianskeho preukazu.",
        "wiki_url": _wiki("Verejná_služba"),
        "stems": [f"verejn{_L} služ"],
    },
    {
        "name": "Zdravotná starostlivosť",
        "short": "Všetko, čo robia lekári a nemocnice pre naše zdravie.",
        "example": "Návšteva všeobecného lekára alebo operácia.",
        "wiki_url": _wiki("Zdravotná_starostlivosť"),
        "stems": [f"zdravotn{_L} starostlivos"],
    },
    {
        "name": "Digitalizácia",
        "short": "Presun služieb a papierov do online sveta.",
        "example": "Žiadosť na úrade vybavíš z mobilu.",
        "wiki_url": _wiki("Digitalizácia"),
        "stems": ["digitaliz", "digitáln"],
    },
    {
        "name": "Byrokracia",
        "short": "Úradné postupy a papierovanie.",
        "example": "Keď potrebuješ päť pečiatok na jednu žiadosť.",
        "wiki_url": _wiki("Byrokracia"),
        "stems": ["byrokra"],
    },
]
