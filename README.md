# Sľubomer

Open-source projekt, ktorý sleduje plnenie politických sľubov na Slovensku.

Každý verdikt stojí len na publikovanom dokumente: zákone, uznesení, rozpočte alebo zmluve. Médiá slúžia len ako tip. Ku každému zdroju evidujeme URL, archivovanú kópiu a hash.

## Stav

Projekt je na začiatku. Repozitár má zatiaľ pravidlá a kostru, kód pribudne.

## Štruktúra

| Priečinok | Obsah |
| --- | --- |
| `ai/` | prompty (`ai/prompts/`), schémy a vyhodnotenie presnosti |
| `backend/` | serverová časť |
| `frontend/` | webové rozhranie |
| `data/` | zdroje, import a testovacie sady |
| `tests/` | testy |
| `docs/` | dokumentácia a metodika |

## Spustenie

Doplní sa, keď pribudne kód. Lokálne nastavenia patria do `.env` (vzor je v `.env.example`).

## Prispievanie

Pred prvou zmenou si prečítaj [CONTRIBUTING.md](CONTRIBUTING.md). Každá zmena ide cez issue a pull request.

## Licencia

Kód je pod licenciou [GPL v3](LICENSE), dáta v `data/` pod [CC BY 4.0](data/LICENSE).
