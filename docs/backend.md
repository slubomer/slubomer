# Backend

Serverová časť Sľubomera: API pre web, redakčné rozhranie a AI pipeline.

Čo a v akom poradí budeme stavať, popisuje [plán vývoja backendu](backend-plan.md).

## Technológie

| Časť | Technológia | Prečo |
| --- | --- | --- |
| Jazyk a API | Python 3.12, FastAPI | rovnaký jazyk ako AI pipeline, automatická API dokumentácia |
| Validácia | Pydantic v2 | súčasť FastAPI, rovnaké modely poslúžia aj ako JSON schéma pre AI |
| Databáza | PostgreSQL 16 + pgvector | dáta aj embeddingy na jednom mieste |
| ORM a migrácie | SQLAlchemy 2.0, Alembic | každá zmena databázy je verzovaná migrácia |
| Konfigurácia | pydantic-settings | nastavenia a tajomstvá len z `.env`, nikdy v kóde |
| Testy a štýl | pytest, ruff | spúšťajú sa aj v CI |

## Štruktúra

```
backend/
  app/
    main.py          # vytvorí FastAPI aplikáciu a pripojí routery
    core/            # konfigurácia (config.py), databáza (db.py), pomocné funkcie na text (text.py)
    models/          # databázové tabuľky, jeden súbor = jedna tabuľka
    schemas/         # Pydantic modely pre requesty a odpovede API
    api/routes/      # endpointy, jeden súbor = jedna oblasť
    services/        # biznis logika, routy ju len volajú
    seed/            # skúšobné dáta z prototypu (python -m app.seed)
    ai/              # AI pipeline (prompty sú v /ai/prompts)
  migrations/        # Alembic migrácie
  tests/             # testy backendu
```

Pravidlo: **routa → služba → model**. Routa spracuje HTTP, logika je v `services/`, prístup k dátam cez modely. Tak sa dá logika testovať aj bez HTTP.

## Spustenie cez Docker (odporúčané)

1. V koreni repozitára skopíruj `.env.example` do `.env` a vyplň `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
2. Spusti:

   ```bash
   docker compose up --build
   ```

3. Over:
   - http://localhost:8000/health → `{"status": "ok"}`
   - http://localhost:8000/health/db → backend sa pripojí k databáze
   - http://localhost:8000/docs → API dokumentácia

Pri štarte sa automaticky spustia migrácie a naimportujú sa sľuby z `data/sluby.json`. Kód je pripojený do kontajnera, zmeny sa prejavia bez nového buildu.

## Spustenie bez Dockeru

Potrebuješ Python 3.12+ a bežiacu databázu (napr. `docker compose up db`). V `.env` vyplň aj `DATABASE_URL` s hostom `localhost`.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

## Verejné API

Všetko je pod `/api/v1`, popis a skúšanie na http://localhost:8000/docs.

| Endpoint | Čo vráti |
| --- | --- |
| `GET /api/v1/promises` | schválené sľuby s publikovaným verdiktom; filtre `q`, `subject`, `category`, `verdict`, `type`, triedenie `sort` (`verified` / `title`), stránkovanie `page`, `page_size` |
| `GET /api/v1/promises/{slug}` | detail: opis sľubu, doslovná citácia so stranou (ak je známa), dôkazy, aktuálny verdikt a história verzií |
| `GET /api/v1/subjects`, `GET /api/v1/categories` | zoznamy pre filtre s počtom sľubov |
| `GET /api/v1/stats/overview` | počet sľubov, rozdelenie podľa verdiktu a počet nehodnotených (`unrated`) |
| `GET /api/v1/stats/subjects` | to isté pre každý subjekt |
| `GET /api/v1/glossary`, `GET /api/v1/glossary/{slug}` | slovník pojmov v slovenskej abecede, s `stems` na zvýraznenie v texte |

Hodnoty verdiktu sú `splneny`, `nesplneny` a `v_procese`. Zoznamy vracajú `{ "items": [...], "total", "page", "page_size" }`.

## Prihlasovanie a roly

Verejné API je bez prihlásenia. Redakčné časti (`/api/v1/admin/...`) vyžadujú prihlásenie a rolu.

| Rola | Hodnota | Čo smie |
| --- | --- | --- |
| Redaktor | `redaktor` | sľuby a dôkazy (B-11) |
| Overovateľ | `overovatel` | schvaľovanie verdiktov (B-12) |
| Admin | `admin` | všetko vrátane správy používateľov, **musí mať zapnutú 2FA** |

### Endpointy

| Endpoint | Čo robí |
| --- | --- |
| `POST /api/v1/auth/login` | prihlásenie e-mailom a heslom, pri zapnutej 2FA aj s `totp_code`; nastaví session cookie |
| `POST /api/v1/auth/logout` | odhlásenie, session sa zmaže aj na serveri |
| `GET /api/v1/auth/me` | prihlásený používateľ |
| `POST /api/v1/auth/2fa/setup` a `/2fa/confirm` | zapnutie 2FA: najprv kľúč (a `otpauth_uri` pre QR kód), potom potvrdenie prvým kódom |
| `POST /api/v1/auth/password` | zmena hesla, ostatné prihlásenia sa ukončia |
| `GET/POST /api/v1/admin/users`, `PATCH /api/v1/admin/users/{id}` | správa používateľov (len admin) |

### Ako to funguje

- **Heslá** sa ukladajú len ako argon2 hash a musia mať aspoň 12 znakov.
- **Session** je náhodný token v httpOnly cookie `slubomer_session` (SameSite=Lax). V databáze (`user_session`) je len jeho SHA-256 hash, platí 12 hodín. Odhlásenie, deaktivácia účtu a zmena hesla session na serveri zmažú.
- **Zablokovanie:** po 5 neúspešných pokusoch za sebou sa účet zablokuje na 15 minút.
- **2FA** je TOTP (Google Authenticator, Aegis, 1Password a pod.).
- **Tabuľka používateľov** sa volá `app_user`, lebo `user` je v PostgreSQL vyhradené slovo.
- **Kontrola rolí v kóde:** `CurrentUser` pre akéhokoľvek prihláseného, `require_role(UserRole.OVEROVATEL)` pre konkrétnu rolu, `AdminUser` pre admina (`app/api/deps.py`).
- **Nastavenia** (`.env`): `COOKIE_SECURE` je predvolene `true` (cookie len cez HTTPS), takže produkcia ho nemôže zabudnúť zapnúť. Lokálne bez Dockeru nastav `COOKIE_SECURE=false`, Docker Compose to robí sám. `CORS_ORIGINS` sú domény frontendu oddelené čiarkou.

### Prvý admin

```bash
docker compose exec backend python -m app.create_admin admin@example.com "Meno Priezvisko"
```

Príkaz sa opýta na heslo a vypíše kľúč 2FA, ktorý si pridáš do aplikácie. Ďalších ľudí potom pridáva admin cez `POST /api/v1/admin/users`. Tí si 2FA zapnú sami po prvom prihlásení.

### Skúšanie v `/docs`

Swagger beží na rovnakej adrese ako API, takže cookie z `POST /api/v1/auth/login` prehliadač automaticky pošle aj pri ďalších volaniach. Stačí sa prihlásiť cez „Try it out“ a potom volať chránené endpointy.

## Audit a verzie verdiktov

Ku každej zmene dát musí byť dohľadateľné, kto ju urobil, kedy a prečo. Publikovaný verdikt sa nikdy neprepisuje.

### Audit log

- Tabuľka `audit_log`: autor (`actor_id`, prázdny pri systémových akciách ako import), akcia, entita a jej id, stará a nová hodnota (`before`, `after`) a dôvod (`reason`).
- Každá služba, ktorá mení dáta, volá `audit.record(...)` (`app/services/audit.py`) **pred** svojím `commit`. Zmena a jej záznam sa tak uložia spolu alebo vôbec.
- Ukladajú sa len zmenené polia. Tajné polia (`password_hash`, `totp_secret`) sa do auditu nikdy nedostanú, pri hesle sa zapíše len `password_reset` alebo `password_changed`.
- Import sľubov zapíše jeden súhrnný záznam (počet nových, dodatočne zaradených do kategórie a preskočených), nie jeden za každý sľub.
- V PostgreSQL databázový trigger odmietne `UPDATE` aj `DELETE` v `audit_log` (migrácia 0005). Funguje aj pre vlastníka databázy.
- Používatelia sa nemažú, len deaktivujú. Používateľa, ktorý je v audite, databáza zmazať nedovolí.
- `GET /api/v1/admin/audit?entity=&entity_id=&actor_id=` vráti záznamy od najnovšieho. Smie ho čítať celá redakcia (redaktor, overovateľ, admin).

Zapisujú sa zmeny používateľov (vytvorenie, úprava, reset a zmena hesla, zapnutie 2FA), import a všetky zmeny cez redakčné API (sľuby, dôkazy, dokumenty, kategórie, slovník). Zmeny verdiktov a námietok pribudnú s B-06 a B-12.

### Verzie verdiktov

- Verdikt v stave `publikovany` alebo `nahradeny` sa nedá zmeniť ani zmazať. Jediná povolená zmena je `publikovany` → `nahradeny`, keď ho nahradí nová verzia.
- Nový obsah znamená nový riadok `verdict` s vyšším číslom verzie. Návrhy (`navrh`, `vrateny`) sa upravovať dajú.
- V PostgreSQL to stráži databázový trigger `verdict_lock` (migrácia 0005), takže pravidlo platí aj pre ručné SQL a hromadné `update()`.
- Navyše to stráži SQLAlchemy udalosť v `app/models/verdict.py`. Tá vyhodí `VerdictLocked` (API vráti 409) a pokrýva aj SQLite v testoch.

## Redakčné API

Redaktor tu dopĺňa a kontroluje sľuby. Overovateľ smie redakčné dáta len čítať, admin (s 2FA) môže všetko. Každá zmena ide do auditu.

| Endpoint | Čo robí |
| --- | --- |
| `GET /api/v1/admin/promises` | Všetky sľuby vrátane návrhov a zamietnutých. Filtre `state`, `subject`, `category`, `without_category`, `q` |
| `GET /api/v1/admin/promises/{id}` | Detail s dôkazmi a všetkými verziami verdiktu, aj návrhmi |
| `POST /api/v1/admin/promises` | Nový sľub ručne. Začína ako `navrh`, verejne viditeľný je až po schválení |
| `PATCH /api/v1/admin/promises/{id}` | Zmení len poslané polia, `null` pole vymaže. Slug (verejný odkaz) sa nemení |
| `POST /api/v1/admin/promises/{id}/approve` | Schváli sľub, objaví sa na webe. Sľub musí mať doslovnú citáciu, stranu a dokument, inak 422 |
| `POST /api/v1/admin/promises/{id}/reject` | Zamietne sľub (napr. nie je to sľub, duplikát). Dôvod je povinný |
| `POST /api/v1/admin/promises/{id}/evidence` | Pridá dôkaz: citát z dokumentu so stranou |
| `DELETE /api/v1/admin/promises/{id}/evidence/{eid}?reason=` | Zmaže dôkaz. Dôvod je povinný, celý dôkaz ostane v audite. Podklad (`podklad`) publikovaného verdiktu sa zmazať nedá (409) |
| `GET/POST /api/v1/admin/documents` | Evidencia dokumentov (druh, názov, URL, dátum). Nahrávanie súboru a hash prídu s B-10 |
| `GET/POST /api/v1/admin/categories`, `PATCH .../{id}` | Správa kategórií. Slug sa pri premenovaní nemení |
| `GET/POST /api/v1/admin/glossary`, `PATCH .../{id}` | Správa slovníka pojmov |

Pravidlá:

- Doslovná citácia (`quote`) a strana (`page`) sú dôkazom toho, čo bolo sľúbené. Prvýkrát sa vyplnia voľne, ich neskoršia zmena vyžaduje `reason`, inak API vráti 422.
- Subjekt a kategória sa posielajú slugom (`"category": "doprava"`), dokument číslom `document_id`.
- Pri zmene názvu, textu, kategórie alebo subjektu sa prepočíta text pre vyhľadávanie (`Promise.refresh_search_text()`).

## Dáta

### Sľuby z volebných programov

`data/sluby.json` obsahuje sľuby strán. Každý záznam má polia `strana`, `nazov`, `telo`, `datum`, `stav` a voliteľne `kategoria`. Import:

```bash
python -m app.import_promises ../data/sluby.json
```

- Strana sa uloží ako `subject` (slug sa vytvorí z názvu), `nazov` ako `title` a `telo` ako `description`.
- Sľuby sa importujú ako **návrhy** (`navrh`) a **bez verdiktu**, takže na verejnom webe ešte nie sú. Zverejní ich až redaktor, keď doplní doslovnú citáciu, stranu a dokument a sľub schváli.
- Pole `stav` sa ignoruje. Formát súboru je zatiaľ len návrh a ešte sa bude meniť.
- `kategoria` sa uloží ako kategória sľubu. Kategória sa vytvorí pri prvom výskyte, ďalšie záznamy s rovnakým názvom ju zdieľajú. Názov poľa je v konštante `CATEGORY_FIELD` v `app/import_promises.py`.
- Typ a doslovná citácia so stranou ostanú prázdne, doplní ich redakcia.
- Import sa dá spustiť opakovane. Sľub, ktorý už v databáze je (rovnaká strana a rovnaký text), preskočí, takisto duplikáty v súbore. Ak však nový súbor prinesie kategóriu a sľub ju ešte nemá, doplní mu ju. Stačí teda nahradiť `data/sluby.json` novou verziou a import spustiť znova.

Docker Compose spúšťa import pri štarte sám, spolu so slovníkom pojmov (`python -m app.seed glossary`).

### Skúšobné dáta z prototypu

`python -m app.seed` nahrá vymyslené dáta z prototypu vo Figme: 3 anonymné subjekty, 4 kategórie, 16 sľubov s verdiktami a dôkazmi a 21 pojmov slovníka. Dokumenty sú označené ako „ukážka“. Používajú sa v testoch a na lokálne skúšanie verdiktov a dôkazov, ktoré skutočné dáta zatiaľ nemajú. Príkaz sa dá spustiť opakovane. `python -m app.seed glossary` nahrá iba slovník (skutočné vysvetlenia pojmov), ten sa nahráva aj v Dockeri.

## Testy a kontrola štýlu

V priečinku `backend/`:

```bash
pytest
ruff check .
ruff format .
```

Rovnaké kontroly beží CI pri každom pull requeste. Testy API bežia nad SQLite v pamäti so skúšobnými dátami (`tests/conftest.py`), takže nepotrebujú Postgres ani Docker.

## Migrácie

Keď pridáš alebo zmeníš model v `app/models/` (a importuješ ho v `app/models/__init__.py`):

```bash
alembic revision --autogenerate -m "add promise table"
alembic upgrade head
```

Vygenerovanú migráciu si vždy prečítaj pred commitom.
