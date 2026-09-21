# RC TNT POC — LangGraph

POC exécutable de l'agent augmenté RC TNT.

## Fonctionnel

- réception d'une alarme DataMiner simulée ;
- acquittement / affectation à l'agent IA ;
- préqualification ;
- détection de doublon ServiceNow ;
- enrichissement DMA / Diabolo ;
- véracité ;
- création de l'INC ;
- recherche historique / récidive ;
- proposition de résolution ;
- policy engine ;
- human-in-the-loop avec `interrupt()` LangGraph ;
- action simulée ;
- recheck ;
- recommandation matériel ;
- clôture ServiceNow.

Les SI sont simulés par de vrais fichiers Excel sous `data/`.

## Codespaces

```bash
pip install -r requirements.txt
python -m app.seed_data
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Ouvrir ensuite le port `8000` depuis l'onglet **PORTS** du Codespace.

## Tests

```bash
pytest -q
```

## Scénarios fournis

- `AL-NEW-001` : nouvel incident, reboot auto, retour normal, clôture.
- `AL-DUP-001` : doublon ServiceNow, pas de nouvel INC.
- `AL-TP-REAL` : TP actif mais panne réelle possible.
- `AL-FALSE-001` : alarme expliquée par maintenance.
- `AL-REC-001` : récidive, remplacement proposé, HITL.
- `AL-FAIL-001` : reboot inefficace, remplacement proposé, HITL.
