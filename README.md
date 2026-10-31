# Sľubomer

Open-source projekt, ktorý sleduje plnenie politických sľubov na Slovensku.

Každý verdikt stojí len na publikovanom dokumente: zákone, uznesení, rozpočte alebo zmluve. Médiá slúžia len ako tip. Ku každému zdroju evidujeme URL, archivovanú kópiu a hash.

## Stav

Projekt je na začiatku. Backend má kostru (FastAPI, PostgreSQL, migrácie), ostatné časti pribudnú.

## Štruktúra

| Priečinok | Obsah |
| --- | --- |
| `ai/` | prompty (`ai/prompts/`), schémy a vyhodnotenie presnosti |
| `backend/` | serverová časť (Python, FastAPI) – [docs/backend.md](docs/backend.md) |
| `frontend/` | webové rozhranie |
| `data/` | zdroje, import a testovacie sady |
| `tests/` | testy |
| `docs/` | dokumentácia a metodika |

## Spustenie

Potrebuješ Docker. Lokálne nastavenia patria do `.env` (vzor je v `.env.example`).

```bash
cp .env.example .env   # vyplň POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
docker compose up --build
```

Backend potom beží na http://localhost:8000 (API dokumentácia na `/docs`). Podrobnosti a spustenie bez Dockeru sú v [docs/backend.md](docs/backend.md).

## Prispievanie

Pred prvou zmenou si prečítaj [CONTRIBUTING.md](CONTRIBUTING.md). Každá zmena ide cez issue a pull request.

## Licencia

Kód je pod licenciou [GPL v3](LICENSE), dáta v `data/` pod [CC BY 4.0](data/LICENSE).
