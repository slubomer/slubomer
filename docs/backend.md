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

## Dáta

### Sľuby z volebných programov

`data/sluby.json` obsahuje sľuby strán. Každý záznam má polia `strana`, `nazov`, `telo`, `datum` a `stav`. Import:

```bash
python -m app.import_promises ../data/sluby.json
```

- Strana sa uloží ako `subject` (slug sa vytvorí z názvu), `nazov` ako `title` a `telo` ako `description`.
- Sľuby sa importujú ako **návrhy** (`navrh`) a **bez verdiktu**, takže na verejnom webe ešte nie sú. Zverejní ich až redaktor, keď doplní doslovnú citáciu, stranu a dokument a sľub schváli.
- Pole `stav` sa ignoruje. Formát súboru je zatiaľ len návrh a ešte sa bude meniť.
- Kategória, typ a doslovná citácia so stranou ostanú prázdne, doplní ich redakcia alebo AI.
- Import sa dá spustiť opakovane. Sľub, ktorý už v databáze je (rovnaká strana a rovnaký text), preskočí, takisto duplikáty v súbore.

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
