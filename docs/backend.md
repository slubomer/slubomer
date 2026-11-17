# Backend

Serverová časť Sľubomera: API pre web, redakčné rozhranie a AI pipeline.

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

## Dáta

### Sľuby z volebných programov

`data/sluby.json` obsahuje sľuby strán. Každý záznam má polia `strana`, `nazov`, `telo`, `datum` a `stav`. Import:

```bash
python -m app.import_promises ../data/sluby.json
```

- Strana sa uloží ako `subject` (slug sa vytvorí z názvu), `nazov` ako `title` a `telo` ako `description`.
- Sľuby sa importujú **bez verdiktu**. Pole `stav` je len zástupná hodnota: verdikt vzniká až po schválení politológom a musí mať dôkaz. Na webe sú také sľuby „zatiaľ nehodnotené“ a štatistiky ich vracajú v poli `unrated`.
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
