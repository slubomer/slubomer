# Metodika hodnotenia sľubov

Tento dokument hovorí, aký stav dostane sľub a podľa čoho. Rovnaké pravidlá platia pre AI aj pre redakciu. Hodnotia sa len sľuby z 9. volebného obdobia NR SR (od roku 2023).

## Stavy

Sľub má vždy jeden zo 4 stavov. V JSON súbore (`stav`), v databáze aj v API sa používajú rovnaké hodnoty:

| Hodnota | Na webe | Význam |
| --- | --- | --- |
| `splnene` | Splnený | Sľub je splnený celý, alebo opozičná strana preukázateľne urobila, čo mohla |
| `ciastocne` | Čiastočne splnený | Práca sa začala alebo je splnená len časť sľubu |
| `porusene` | Porušený | Sľub zhodili poslanci strany, ktorá ho dala |
| `nesplnene` | Nesplnený | Nenašiel sa žiadny dôkaz, že sa plnenie začalo |

Každý stav má zdôvodnenie (`zdovodnenie`, v databáze `explanation`) napísané jednoducho a istotu (`confidence`, 0 až 1). AI môže vo vnútri redakcie vrátiť aj `nedostatok_informacii`. Tá sa nikdy nepublikuje.

## Pravidlá

### Hlasovania v parlamente

1. **Zákon prešiel** a sľubu sa týka podľa zámeru → `splnene`.
2. **Zákon neprešiel kvôli poslancom strany**, ktorá sľub dala → `porusene`. Ústavný zákon potrebuje 90 hlasov, ostatné zákony väčšinu prítomných poslancov. Zdôvodnenie uvedie počty hlasov a koľko chýbalo. Strana zákon zhodila, ak by s hlasmi celého svojho klubu prešiel.
3. **Zákon neprešiel, ale celý klub strany hlasoval Za** (zhodil ho niekto iný):
   - strana vládnej koalície (v 9. období SMER-SD, HLAS-SD a SNS) → `ciastocne`,
   - opozičná strana, ktorá návrh predložila alebo podporila → `splnene` (preukázateľná snaha).
4. **Prešlo len prvé čítanie** → `ciastocne` (práca sa začala).

### Sľub s viacerými časťami

Sľub môže mať viac častí, napríklad dva zákony alebo viac stavieb či opatrení. Ak je splnená aspoň jedna časť, ale nie všetky → `ciastocne`. Zdôvodnenie vymenuje, čo je splnené a čo ešte nie. Ak sú splnené všetky časti → `splnene`.

### Kedy sa „začalo pracovať“

Musí existovať konkrétny krok štátu: prijatý zákon alebo uznesenie vlády, podpísaná zmluva, vyhlásené obstarávanie, začatá stavba alebo schválené financovanie. Samotné vyhlásenie zámeru, štúdia ani plán nestačia → `nesplnene`.

### Dôkazy

- Keď dôkaz nie je v hlasovaniach, hľadá sa na webe: Slov-Lex, rokovania.gov.sk, ministerstvá, MF SR, CRZ, ŠÚ SR, TASR, SITA, noviny.sk. Nájdený dôkaz sa zapíše do `vyhodnotenie`.
- Ak sa nič nenájde, `vyhodnotenie` ostane prázdne, stav je `nesplnene` a zdôvodnenie to povie („Nenašiel sa žiadny dôkaz o začatí plnenia.“).
- Sľub s viacerými dôkazmi dostane najlepší z nich v poradí `splnene` > `ciastocne` > `porusene` > `nesplnene`.
- Rozlišuje sa návrh, schválenie, vyhlásenie a účinnosť. Rozpočet nie je čerpanie.
- Počíta sa len 9. volebné obdobie. Dôkaz spred roku 2023 sa nezapisuje. Ak iný nie je, stav je `nesplnene` a zdôvodnenie to uvedie.
- Pri slabej, iba tematickej zhode sa dôkaz nezapisuje. Ak sa dá záver urobiť len s výhradou, dostane nízku istotu a ide na kontrolu redakcii.

### Médiá a publikovanie

Verdikt z AI sa zverejní hneď, s označením, že ho hodnotil AI. Môže stáť aj na článku z médií (dôkaz typu `web`), lebo pre mnohé stavby a opatrenia iný verejný zdroj nie je.

Označenie **overený politológom** dostane verdikt, až keď ho politológ potvrdí publikovaným dokumentom, napríklad zákonom, uznesením, zmluvou alebo hlasovaním NR SR. Článok z médií na overenie nestačí (pozri [CONTRIBUTING](../CONTRIBUTING.md)). Výnimkou je `nesplnene`, ktorý hovorí, že sa dôkaz nenašiel. Komentár politológa k sľubu je od overenia oddelený: pridanie komentára verdikt neoverí.

## Kde sa pravidlá používajú

- `data/sluby.json`: stavy v súbore sú vypočítané podľa týchto pravidiel (`meta.kroky`, krok `prepocet_stavov`).
- Backend: hodnoty sú v `VerdictValue` v `backend/app/models/enums.py`. Import ich preberie bez prekladu (pozri [backend.md](backend.md#sľuby-z-volebných-programov)).
- AI návrh verdiktu (B-14) bude používať tieto pravidlá v prompte v `ai/prompts/`. Prompt nesmie obsahovať názvy strán, zoznam koaličných strán dostane ako vstup.
