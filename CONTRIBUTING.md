# Pravidlá prispievania – Sľubomer

Krátke pravidlá pre tím. Platia pre kód, prompty, dáta aj dokumentáciu.

## 1. Základ

- Do `main` sa **nikdy necommituje priamo**. Každá zmena ide cez **pull request (PR)**.
- Každý PR schváli aspoň **1 iný člen tímu**. Vlastný PR si nikto nemerguje bez review.
- Každá práca má **Issue**. Bez issue sa nezačína (výnimka: preklep v dokumentácii).
- `main` musí byť vždy funkčný – testy a CI prechádzajú.

## 2. Vetvy

Formát: `typ/<číslo-issue>-kratky-popis`

| Typ | Kedy | Príklad |
| --- | --- | --- |
| `feature/` | nová funkcia | `feature/12-zoznam-slubov` |
| `fix/` | oprava chyby | `fix/31-filter-strana` |
| `docs/` | dokumentácia | `docs/8-readme` |
| `data/` | zdroje, import, testovacie sady | `data/15-import-pvv` |
| `ai/` | prompty, schémy, vyhodnotenie | `ai/20-prompt-extrakcia-v2` |
| `chore/` | nastavenie repozitára, CI, závislosti | `chore/5-ci` |

Vetvy sú krátkodobé – merge do pár dní, potom sa zmažú.

## 3. Commity

Formát [Conventional Commits](https://www.conventionalcommits.org/), anglicky, rozkazovacím spôsobom:

```
feat: add promise list filters
fix: correct page number in citation
docs: describe verdict levels
test: add extraction tests against gold standard
chore: update dependencies
```

Malé commity, jedna logická zmena = jeden commit.

## 4. Pull request

- Názov ako commit (`feat: ...`), v popise `Closes #<číslo>`.
- PR je malý – ideálne do ~400 riadkov zmien. Veľké veci rozdeľ.
- Pred otvorením: lokálne prejdú testy a linter, vetva je aktuálna voči `main`.
- Reviewer odpovie do **48 hodín** (cez víkend neplatí).
- Merge: **Squash and merge**. Po merge zmaž vetvu.

**Checklist do popisu PR:**

```
- [ ] Closes #
- [ ] Testy prechádzajú / pridal som nové
- [ ] Žiadne heslá, API kľúče ani .env v commite
- [ ] Ak meníš prompt alebo model: nová verzia + výsledok testu presnosti
- [ ] Ak meníš UI: stav nie je označený iba farbou (WCAG 2.1 AA)
```

## 5. Tajomstvá a bezpečnosť

- **Žiadne heslá, tokeny ani API kľúče v repozitári.** Ani v histórii, ani „len na chvíľu“.
- Lokálne nastavenia sú v `.env` (je v `.gitignore`). Do repozitára ide len `.env.example` s prázdnymi hodnotami.
- Ak niečo uniklo: hneď povedz v tímovom chate, kľúč sa **zneplatní a vymení**. Zmazanie commitu nestačí.

## 6. AI a prompty

- Prompty sú v `ai/prompts/` ako súbory, nie natvrdo v kóde.
- Každá zmena promptu alebo modelu = **nová verzia** (napr. `extract_promises_v3.md`) a **nový test presnosti**; výsledok ide do PR.
- Prompty **neobsahujú názvy strán ani hodnotiace slová**. Jeden prompt pre všetky strany, žiadne výnimky v kóde.
- Výstup AI je JSON podľa schémy, teplota 0.

## 7. Dáta

- Verdikt stojí **len na publikovanom dokumente** (zákon, uznesenie, rozpočet, zmluva). Médiá sú len tip.
- Každý zdroj má URL, archivovanú kópiu a hash.
- Veľké súbory (PDF, dumpy) nepatria do gitu – ukladajú sa mimo repozitára, v gite je len odkaz a hash.
- Žiadne osobné údaje mimo verejného výkonu funkcie (GDPR).

## 8. Nestrannosť

- V issues, commitoch, PR ani kóde **žiadne politické komentáre** ani názory na strany či politikov.
- Píšeme vecne: čo je v dokumente, nie čo si o tom myslíme.

## 9. Jazyk

- Kód, názvy premenných, commity: **angličtina**.
- Issues, dokumentácia, metodika: **slovenčina**.

## 10. Kto je zodpovedný za čo

| Oblasť | Zodpovedný | Priečinok |
| --- | --- | --- |
| AI | Richard Balog | `ai/` |
| Backend | Patrik Lihan | `backend/` |
| Frontend | Samuel Zapotocký | `frontend/` |
| Dáta a testovanie | Adam Melničák | `data/`, `tests/` |
| UX a dokumentácia | Marianna Mikolajová | `docs/` |

Zodpovedný robí review zmien vo svojom priečinku (nastavené v `.github/CODEOWNERS`).
