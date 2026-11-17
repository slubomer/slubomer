# Plán vývoja backendu

Tento plán hovorí, čo bude backend Sľubomera robiť, v akom poradí ho budeme stavať a kedy je každá časť hotová. Vychádza z projektového zámeru, z analýzy požiadaviek (F-01 až F-08) a z prototypu vo Figma Make. Ako backend spustiť a ako je usporiadaný kód, popisuje [backend.md](backend.md).

Každá funkcia (B-01 až B-16) má vlastnú kartu v Trelle, vlastné issue a vlastnú vetvu. Plán je živý dokument: keď sa niečo zmení, upravíme ho v tom istom PR.

## 1. Východiská

**Stav:** kostra backendu je v `main` (PR #12). Obsahuje FastAPI, PostgreSQL 16 s pgvector, Alembic, Docker Compose, pytest, ruff a CI.

**Termíny:**

| Šprint | Termín | Čo zo zámeru |
| --- | --- | --- |
| 4 | 12. 11. – 25. 11. | AI navrhuje verdikty, test presnosti na 50 sľuboch, detail sľubu |
| 5 | 26. 11. – 9. 12. | redakcia a schvaľovanie, AI pipeline v backende |
| 6 | 10. 12. – 23. 12. | export, nasadenie, dolaďovanie |
| rezerva | 24. 12. – 31. 12. | opravy, launch v januári 2027 |

Šprinty 5 a 6 sú náš návrh. Zámer presne určuje len šprinty 3 a 4.

**Pravidlá zo zámeru, ktoré musí backend dodržať vždy:**

- Publikovaný verdikt sa nikdy neprepisuje. Každá zmena je nová verzia a záznam v histórii.
- Každý AI krok sa loguje: vstup, prompt a jeho verzia, model, výstup a istota.
- Verdikt stojí len na publikovanom dokumente. Každý zdroj má URL, archivovanú kópiu a hash.
- AI vracia JSON podľa schémy pri teplote 0 a cituje doslovne aj s číslom strany. V promptoch nie sú názvy strán.
- Žiadne tajomstvá v repozitári, žiadne osobné údaje mimo verejného výkonu funkcie (GDPR). Obsah od AI je označený (AI Act).

## 2. Architektúra v skratke

```
Verejný web (Next.js) ──┐
Redakčné rozhranie ─────┼──> FastAPI /api/v1 ──> služby (services/) ──> PostgreSQL + pgvector
                        │                              │
                        │                              └──> AI pipeline (app/ai/) ──> LLM API
                        └── export CSV / JSON
```

- Kód ide cestou **routa → služba → model** (viď [backend.md](backend.md)).
- **Verejné API** (`/api/v1/...`) je bez prihlásenia a len na čítanie. Výnimkou je odoslanie námietky.
- **Redakčné API** (`/api/v1/admin/...`) vyžaduje prihlásenie a rolu.
- **AI úlohy** bežia na pozadí a nie v requeste, lebo spracovanie PDF trvá dlho. Začneme jednoduchou tabuľkou úloh, ktorú spracúva samostatný worker. Ak to nebude stačiť, prejdeme na frontu (napr. arq + Redis).
- **Súbory** (PDF, archivované kópie) sú mimo gitu, v úložisku na disku servera (Docker volume). V databáze je len cesta k súboru a jeho SHA-256 hash.

### Dohody pre API

- Prefix `/api/v1`, JSON, názvy polí v angličtine a v `snake_case`.
- Zoznamy sa stránkujú a vracajú `{ "items": [...], "total": 42, "page": 1, "page_size": 20 }`.
- Chyby vracajú `{ "detail": "..." }` so správnym HTTP kódom (400, 401, 403, 404, 409, 422, 429).
- V URL sa používa `slug` (napr. `/promises/zvysime-platy-ucitelov`). Vnútorné ID je celé číslo.
- Kontrakt s frontendom je OpenAPI na `/docs`. Pydantic schémy v `app/schemas/` sú zdrojom pravdy.

## 3. Dátový model

Tabuľky zo zámeru (subjekt, dokument, sľub, dôkaz, verdikt, ai_beh, audit) doplnené o to, čo potrebuje prototyp: kategórie, slovník a námietky. Názvy sú v kóde anglicky.

| Tabuľka | Na čo slúži | Hlavné stĺpce |
| --- | --- | --- |
| `subject` | politická strana alebo hnutie | `name`, `short_name`, `slug` |
| `category` | téma sľubu | `slug`, `label`, `tagline` |
| `document` | programový dokument alebo dôkaz | `subject_id`, `kind` (program / zákon / uznesenie / rozpočet / zmluva / iné), `title`, `url`, `archived_path`, `sha256`, `published_at`, `fetched_at` |
| `document_chunk` | text dokumentu po stranách a embedding pre vyhľadávanie | `document_id`, `page`, `text`, `embedding` (pgvector) |
| `promise` | sľub | `slug`, `subject_id`, `document_id`, `category_id`, `title`, `quote` (doslovne), `page`, `type` (konkrétny / zákon / stavba / vágny), `state` (návrh / schválený / zamietnutý), `ai_run_id` |
| `evidence` | dôkaz k sľubu | `promise_id`, `document_id`, `page`, `quote`, `role` (zdroj sľubu / podklad k hodnoteniu), `ai_run_id`, `added_by` |
| `verdict` | verzia hodnotenia sľubu | `promise_id`, `version`, `value`, `explanation`, `state` (návrh / vrátený / publikovaný / nahradený), `confidence`, `ai_run_id`, `reviewed_by`, `review_reason`, `published_at` |
| `ai_run` | log jedného AI kroku | `step` (extrakcia / dôkazy / verdikt), `prompt_name`, `prompt_version`, `model`, `input`, `output`, `confidence`, `tokens`, `duration_ms`, `error` |
| `job` | úloha na pozadí | `kind`, `payload`, `status`, `attempts`, `error` |
| `audit_log` | kto, čo a kedy zmenil | `actor_id`, `action`, `entity`, `entity_id`, `before`, `after`, `reason`, `created_at` |
| `glossary_term` | pojem v slovníku | `slug`, `name`, `short`, `long`, `example`, `wiki_url`, `stems` |
| `objection` | námietka od verejnosti | `promise_id`, `type` (verdikt / dôkaz / citácia / iné), `text`, `link`, `email`, `status`, `resolution`, `handled_by` |
| `user` | člen redakcie | `email`, `password_hash`, `role` (redaktor / overovateľ / admin), `totp_secret`, `is_active` |

**Hodnoty verdiktu** (`value`): `splneny`, `ciastocne_splneny`, `v_procese`, `nesplneny`, `mimo_kompetencie`, `nemeratelny`. AI môže navrhnúť aj `nedostatok_informacii`, tá sa však nikdy nepublikuje.

**Verzovanie:** sľub má vždy najviac jeden publikovaný verdikt. Nová verzia staršiu označí ako `nahradeny` a nemaže ju. Detail sľubu z týchto verzií skladá históriu.

> **Rozdiel oproti prototypu:** Figma Make pozná len 3 stavy (splnený, nesplnený, v procese). Zámer ich má 6. API bude vracať všetkých 6 a dizajn treba doplniť. Rieši to UX (Marianna) a frontend (Samuel).

## 4. Funkcie a kroky

Poradie je zvolené tak, aby frontend čo najskôr mohol nahradiť vymyslené dáta z prototypu skutočným API. Až potom príde redakcia a AI.

### Fáza 1: dáta a verejné čítanie (šprint 4)

#### B-01 Dátový model, migrácie a seed dáta

Tabuľky z kapitoly 3 a skúšobné dáta, s ktorými môže frontend hneď pracovať.

1. SQLAlchemy modely v `app/models/`, jeden súbor = jedna tabuľka. Enumy pre stavy a hodnoty.
2. Alembic migrácia, prečítaná pred commitom.
3. Indexy: `promise(subject_id, category_id, type)`, fulltext na `title` + `quote` (slovenská konfigurácia, bez diakritiky cez `unaccent`), HNSW na `document_chunk.embedding`.
4. Seed skript `python -m app.seed`: 3 subjekty, 4 kategórie, 16 sľubov, slovník (21 pojmov) a verdikty, všetko z prototypu.
5. Testy: migrácia prebehne na čistej databáze a seed sa dá spustiť aj opakovane.

**Hotovo, keď** `alembic upgrade head` a seed prebehnú bez chyby a v databáze sú dáta z prototypu.

#### B-02 API: zoznam sľubov, filtre a vyhľadávanie (F-02)

- `GET /api/v1/promises?q=&subject=&category=&verdict=&type=&sort=&page=&page_size=`
- `GET /api/v1/subjects`, `GET /api/v1/categories` (číselníky pre filtre, s počtom sľubov)

1. Pydantic schémy `PromiseListItem` a `Page[T]`.
2. Služba `promise_service.search()`: kombinuje filtre, fulltext ignoruje diakritiku, triedi podľa relevancie alebo dátumu overenia.
3. Verejne sa zobrazia len schválené sľuby a ich publikovaný verdikt.
4. Testy pre každý filter, ich kombináciu, prázdny výsledok a stránkovanie.

**Hotovo, keď** obrazovka „Sľuby“ z prototypu funguje len s týmto API.

#### B-03 API: detail sľubu s dôkazmi a históriou (F-03)

- `GET /api/v1/promises/{slug}`

1. Odpoveď obsahuje sľub, doslovnú citáciu so stranou, zdrojový dokument, dôkazy (URL, archivovanú kópiu, stranu, citáciu), aktuálny verdikt s vysvetlením a históriu verzií.
2. Pri obsahu od AI je príznak `ai_generated` (AI Act). Pri verdikte je rola overovateľa, bez osobných údajov.
3. `GET /api/v1/documents/{id}/archive` vráti archivovanú kópiu.
4. Testy: neexistujúci slug vráti 404, neschválený sľub sa nezobrazí, história je v správnom poradí.

**Hotovo, keď** obrazovka „Detail“ z prototypu vrátane náhľadu dôkazu funguje len s týmto API.

#### B-04 API: prehľad a štatistiky (F-01)

- `GET /api/v1/stats/overview` vráti počty podľa verdiktu.
- `GET /api/v1/stats/subjects` vráti počty podľa subjektu a verdiktu (grafy „Kto plní sľuby?“).
- „Čerstvo overené“ = `GET /api/v1/promises?sort=-verified_at&page_size=3`.

1. Agregácia v SQL, nie v Pythone.
2. Krátka cache (napr. 60 s), lebo úvodná stránka je najnavštevovanejšia.
3. Testy: súčty sedia so zoznamom sľubov.

**Hotovo, keď** úvodná obrazovka z prototypu funguje len s týmto API.

#### B-05 API: slovník pojmov

- `GET /api/v1/glossary` vráti pojmy zoradené podľa slovenskej abecedy.
- `GET /api/v1/glossary/{slug}`

1. Odpoveď obsahuje aj `stems`, aby frontend vedel v texte zvýrazniť skloňované tvary, rovnako ako v prototype.
2. Úpravy pojmov pre redakciu prídu s B-11.
3. Testy: správne zoradenie (Č, Š, Ž), 404 pre neznámy pojem.

**Hotovo, keď** obrazovka „Slovník“ a vysúvacie okno s pojmom fungujú s API.

### Fáza 2: interakcia s verejnosťou (šprinty 4–5)

#### B-06 Námietky (F-07)

- `POST /api/v1/promises/{slug}/objections` (bez prihlásenia)
- `GET/PATCH /api/v1/admin/objections` (redakcia, až po B-08)

1. Validácia: typ je povinný, text má 10 až 2000 znakov, odkaz musí byť URL, e-mail je nepovinný.
2. Ochrana pred spamom: limit na IP (napr. 5 za hodinu) a skryté pole proti robotom.
3. GDPR: e-mail sa použije len na odpoveď a po vybavení sa po 90 dňoch zmaže (úloha na pozadí).
4. Stavy: nová → v riešení → vyriešená / zamietnutá. Zmena stavu ide do auditu.
5. Testy: platná námietka, chybné vstupy, prekročený limit.

**Hotovo, keď** formulár z prototypu reálne odošle námietku a redakcia ju vidí v zozname.

#### B-07 Otvorené dáta: export (F-08)

- `GET /api/v1/export/promises.{csv,json}`
- `GET /api/v1/export/evidence.{csv,json}`
- `GET /api/v1/export/verdicts.{csv,json}` (celá história verzií)

1. Exportuje sa len publikovaný obsah, bez e-mailov a interných poznámok.
2. Odpoveď sa streamuje, aby veľký export nezahltil pamäť.
3. V hlavičke a v JSON metadátach je licencia CC BY 4.0 a dátum exportu.
4. Metodika je statický obsah na frontende. Backend ju nepotrebuje.
5. Testy: CSV sa dá otvoriť (UTF-8 s BOM pre Excel), počty sedia s API.

**Hotovo, keď** všetky tri tlačidlá na obrazovke „Otvorené dáta“ stiahnu skutočný súbor.

### Fáza 3: redakcia (šprint 5)

#### B-08 Prihlasovanie, roly a 2FA

1. Tabuľka `user`, heslá hashované cez argon2.
2. `POST /api/v1/auth/login` a `POST /api/v1/auth/logout`. Session v httpOnly cookie (zvládne to aj Next.js a nie je to token v localStorage).
3. TOTP 2FA (napr. `pyotp`), povinné pre admina, odporúčané pre ostatných.
4. Závislosti `require_role("editor" | "verifier" | "admin")` pre FastAPI routy.
5. Admin spravuje používateľov: `GET/POST/PATCH /api/v1/admin/users`. Prvého admina vytvorí CLI príkaz.
6. Ochrana: limit pokusov o prihlásenie a CORS len pre naše domény.
7. Testy: každá rola smie len to, čo má, a zlé heslo či 2FA kód neprejde.

**Hotovo, keď** sa redaktor, overovateľ aj admin vedia prihlásiť a každý vidí len svoje časti.

#### B-09 Audit log a verzovanie verdiktov

1. Služba `audit.record(actor, action, entity, before, after, reason)` volaná z každej služby, ktorá mení dáta.
2. Verdikt nemá update endpoint. Jediná cesta je nová verzia (pravidlo v službe a test, ktorý to stráži).
3. Databázové práva: aplikácia smie do `audit_log` len zapisovať, nie meniť ani mazať.
4. `GET /api/v1/admin/audit?entity=&entity_id=` pre redakciu.
5. Testy: každá zmena sľubu, dôkazu, verdiktu a námietky zanechá záznam.

**Hotovo, keď** sa ku každému publikovanému verdiktu dá dohľadať, kto ho kedy a prečo zmenil.

#### B-10 Dokumenty: nahrávanie PDF, archivácia a hash

- `POST /api/v1/admin/documents` (nahratie PDF alebo zadanie URL)
- `GET /api/v1/admin/documents`

1. Pri URL backend stiahne a uloží kópiu. Pri súbore ho uloží. V oboch prípadoch spočíta SHA-256.
2. Rovnaký hash = rovnaký dokument, duplikát sa neuloží.
3. Text sa vytiahne po stranách (napr. `pymupdf`) do `document_chunk`, aby AI vedela citovať stranu.
4. Limity: iba PDF, max. veľkosť napr. 50 MB, kontrola typu súboru podľa obsahu.
5. Testy: hash, duplikát, PDF bez textovej vrstvy (zalogovať a označiť, OCR riešime neskôr).

**Hotovo, keď** redaktor nahrá program strany a v databáze je dokument s hashom, kópiou a textom po stranách.

#### B-11 Redakčné API: správa sľubov

- `GET/POST/PATCH /api/v1/admin/promises`
- `POST /api/v1/admin/promises/{id}/approve` a `.../reject`
- `POST/DELETE /api/v1/admin/promises/{id}/evidence`
- `GET/POST/PATCH /api/v1/admin/glossary`

1. Redaktor vidí sľuby navrhnuté AI, opraví názov, kategóriu a typ, potom ich schváli alebo zamietne.
2. Doslovnú citáciu a stranu nemožno upraviť bez zdôvodnenia, lebo musia sedieť s dokumentom.
3. Redaktor môže ručne pridať dôkaz z nahraného dokumentu.
4. Všetko ide do auditu (B-09).
5. Testy: oprávnenia podľa rolí a prechody stavov.

**Hotovo, keď** redaktor vie prejsť sľuby z jedného programu od návrhu po schválenie.

#### B-12 Overovanie verdiktov politológom (F-06)

- `GET /api/v1/admin/verdicts?state=navrh`
- `POST /api/v1/admin/verdicts/{id}/approve`, `.../edit`, `.../return` (dôvod je vždy povinný)

1. Schválenie publikuje verdikt, predošlú verziu označí ako nahradenú a nastaví `published_at`.
2. Úprava vytvorí novú verziu s hodnotou a vysvetlením od overovateľa a odkazom na pôvodný návrh AI.
3. Vrátenie pošle sľub späť redaktorovi alebo na nové hľadanie dôkazov.
4. Publikovať sa dá len verdikt, ktorý má aspoň jeden dôkaz z publikovaného dokumentu.
5. Testy: bez dôvodu to neprejde, `nedostatok_informacii` sa nedá publikovať, história ostane celá.

**Hotovo, keď** overovateľ vie schváliť, upraviť aj vrátiť verdikt a na verejnom webe sa ukáže až schválená verzia.

### Fáza 4: AI pipeline (šprinty 4–6, spolu s Richardom)

Prompty, schémy a vyhodnotenie presnosti má na starosti AI (Richard). Backend ich spúšťa, ukladá a loguje. Prompty sú súbory v `ai/prompts/`, backend ich načíta podľa názvu a verzie.

#### B-13 AI extrakcia sľubov z PDF (F-04)

1. Spoločný klient na LLM v `app/ai/`: teplota 0, JSON výstup, validácia cez Pydantic schému, opakovanie pri chybe, kľúč len z `.env`.
2. Každé volanie zapíše `ai_run` (prompt a verzia, model, vstup, výstup, istota, tokeny, čas).
3. Úloha na pozadí: dokument → po častiach na extrakciu → návrhy sľubov so stavom `navrh`.
4. Kontrola citácie: doslovný text musí naozaj byť na uvedenej strane. Ak nie je, sľub dostane príznak na kontrolu.
5. `POST /api/v1/admin/documents/{id}/extract` spustí úlohu, `GET /api/v1/admin/jobs/{id}` vráti jej stav.
6. Testy s falošným LLM klientom, aby nepotrebovali API kľúč.

**Hotovo, keď** po nahratí programu vzniknú návrhy sľubov s citáciou a stranou a každý krok je v `ai_run`.

#### B-14 AI dôkazy a návrh verdiktu (F-05)

1. Embeddingy textu dokumentov do `document_chunk` (pgvector).
2. Hľadanie kandidátov na dôkaz: najprv vektorové a fulltextové hľadanie v našich dokumentoch, potom AI vyberie relevantné úryvky.
3. Návrh verdiktu: AI dostane sľub a dôkazy a vráti hodnotu, krátke vysvetlenie, citáciu a istotu. Môže vrátiť aj `nedostatok_informacii`.
4. Výsledok je `verdict` so stavom `navrh`. Odtiaľ ide k overovateľovi (B-12).
5. Testy s falošným LLM klientom: dôkaz bez citácie sa neuloží, výstup mimo schémy skončí chybou v `ai_run`.

**Hotovo, keď** pre schválený sľub vznikne návrh verdiktu s aspoň jedným citovaným dôkazom.

#### B-15 Vyhodnotenie presnosti AI

1. Príkaz `python -m app.ai.evaluate --set gold_v1`: spustí pipeline na zlatom štandarde (50, neskôr 150 sľubov) a porovná výsledok s politológom.
2. Výstup: zhoda verdiktov v % (cieľ 80 %), presnosť citácií a matica zámen. Uloží sa ako JSON a pridá do PR.
3. Každá nová verzia promptu alebo modelu = nové spustenie (pravidlo z CONTRIBUTING).
4. Zlatý štandard pripravuje tím dát (Adam), backend dodá formát a nástroj.

**Hotovo, keď** jeden príkaz vypíše presnosť pre danú verziu promptu a výsledok sa dá porovnať s minulou verziou.

### Fáza 5: nasadenie (šprint 6)

#### B-16 Nasadenie na VPS a prevádzka

1. Produkčný Docker Compose: backend (gunicorn + uvicorn workers), worker, PostgreSQL, reverzná proxy s HTTPS (napr. Caddy).
2. GitHub Actions: build a nasadenie z `main` po prejdení CI. Tajomstvá sú v GitHub Secrets.
3. Zálohy databázy a súborov každý deň, raz otestovaná obnova.
4. Logy v JSON, `/health` pre monitoring, upozornenie pri výpadku.
5. Bezpečnosť: CORS, rate limit, hlavičky (HSTS a pod.), aktualizácie závislostí (Dependabot).
6. Dokumentácia nasadenia v `docs/`.

**Hotovo, keď** beží verejná adresa s HTTPS, nasadzuje sa automaticky a záloha sa dá obnoviť.

## 5. Závislosti medzi funkciami

```
B-01 ──> B-02, B-03, B-04, B-05, B-06, B-07
B-08 ──> B-09 ──> B-10, B-11, B-12
B-10 ──> B-13 ──> B-14 ──> B-15
B-11, B-14 ──> B-12
všetko ──> B-16
```

B-02 až B-05 sa dajú robiť súbežne, rovnako B-06 a B-07.

## 6. Otvorené otázky

| Otázka | Koho sa týka |
| --- | --- |
| Prototyp má 3 stavy verdiktu, zámer 6. Doplniť dizajn? | UX, frontend |
| Ktorý LLM (API alebo open-weight) a kto platí API kľúč? | AI, tím |
| Majú mať 2FA aj redaktor a overovateľ, nielen admin? | tím |
| Zobrazovať meno overovateľa pri verdikte, alebo len rolu? (GDPR) | tím, metodika |
| Fotky k sľubom: vlastné, z fotobanky, alebo žiadne? | UX |
| Kde bude bežať VPS a kto ho spravuje? | tím, iiTeam |
