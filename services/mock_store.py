from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class MockStore:
    def __init__(self) -> None:
        self._lock = RLock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not (DATA_DIR / "dataminer.xlsx").exists():
            self.reset()

    def reset(self) -> None:
        with self._lock:
            alarms = pd.DataFrame([
                {"alarm_id":"AL-NEW-001","IG":"IG100","PS":"PS100","equipment":"EMET-TNT-01","alarm":"POWER_LOW","description":"Baisse de puissance RF sur émetteur TNT","severity":"Major","status":"Active","site":"SITE-PAR-01","scenario":"new","ack":"no","assigned_to":"","last_action":""},
                {"alarm_id":"AL-DUP-001","IG":"IG200","PS":"PS200","equipment":"EMET-TNT-02","alarm":"LOSS_OF_SIGNAL","description":"Perte du signal principal émetteur TNT","severity":"Critical","status":"Active","site":"SITE-LYO-02","scenario":"dup","ack":"no","assigned_to":"","last_action":""},
                {"alarm_id":"AL-TP-REAL","IG":"IG300","PS":"PS300","equipment":"EMET-TNT-03","alarm":"POWER_LOW","description":"Perte de puissance pendant intervention planifiée","severity":"Major","status":"Active","site":"SITE-NAN-03","scenario":"tp","ack":"no","assigned_to":"","last_action":""},
                {"alarm_id":"AL-FALSE-001","IG":"IG400","PS":"PS400","equipment":"EMET-TNT-04","alarm":"MAINT_MODE","description":"Alarme liée à une maintenance connue","severity":"Minor","status":"Active","site":"SITE-LIL-04","scenario":"false","ack":"no","assigned_to":"","last_action":""},
                {"alarm_id":"AL-REC-001","IG":"IG500","PS":"PS500","equipment":"EMET-TNT-05","alarm":"POWER_LOW","description":"Nouvelle perte de puissance RF récurrente","severity":"Major","status":"Active","site":"SITE-STR-05","scenario":"rec","ack":"no","assigned_to":"","last_action":""},
                {"alarm_id":"AL-FAIL-001","IG":"IG600","PS":"PS600","equipment":"EMET-TNT-06","alarm":"POWER_LOW","description":"Baisse puissance persistante après reboot","severity":"Major","status":"Active","site":"SITE-BDX-06","scenario":"fail","ack":"no","assigned_to":"","last_action":""},
            ])

            incidents = pd.DataFrame([
                {"number":"INC0001001","IG":"IG200","PS":"PS200","short_description":"Perte signal émetteur TNT","description":"Perte du signal principal sur EMET-TNT-02","state":"In Progress","resolution_notes":"","equipment":"EMET-TNT-02","site":"SITE-LYO-02","age_days":0},
                {"number":"INC0002001","IG":"IG500","PS":"PS500","short_description":"Baisse puissance RF","description":"Puissance RF instable EMET-TNT-05","state":"Closed","resolution_notes":"Reboot émetteur effectué, retour normal","equipment":"EMET-TNT-05","site":"SITE-STR-05","age_days":14},
                {"number":"INC0002002","IG":"IG500","PS":"PS500","short_description":"Nouvelle baisse puissance RF","description":"Récidive puissance faible EMET-TNT-05","state":"Closed","resolution_notes":"Reboot amplificateur PA, retour normal temporaire","equipment":"EMET-TNT-05","site":"SITE-STR-05","age_days":32},
                {"number":"INC0002003","IG":"IG500","PS":"PS500","short_description":"Défaut PA émetteur","description":"Troisième récidive puissance faible EMET-TNT-05","state":"Closed","resolution_notes":"Remplacement recommandé si nouvelle récidive","equipment":"EMET-TNT-05","site":"SITE-STR-05","age_days":70},
            ])

            dma = pd.DataFrame([
                {"alarm":"POWER_LOW","equipment_type":"TRANSMITTER","consigne":"Vérifier PA et niveau RF","action":"REBOOT","runbook":"RB-TNT-01"},
                {"alarm":"LOSS_OF_SIGNAL","equipment_type":"TRANSMITTER","consigne":"Vérifier flux et entrée RF","action":"CHECK_INPUT","runbook":"RB-TNT-02"},
                {"alarm":"MAINT_MODE","equipment_type":"TRANSMITTER","consigne":"Vérifier maintenance planifiée","action":"NO_ACTION","runbook":"RB-TNT-03"},
            ])

            diabolo = pd.DataFrame([
                {"site":"SITE-NAN-03","equipment":"EMET-TNT-03","technician":"TECH-07","status":"IN_PROGRESS","intervention":"Maintenance programmée PA","can_cause_failure":"yes"},
                {"site":"SITE-LIL-04","equipment":"EMET-TNT-04","technician":"TECH-12","status":"IN_PROGRESS","intervention":"Maintenance test mode","can_cause_failure":"no"},
            ])

            material = pd.DataFrame([
                {"equipment":"EMET-TNT-05","reference":"PA-500","type":"Amplificateur","replacement":"PA-500-R2","stock":"AVAILABLE"},
                {"equipment":"EMET-TNT-06","reference":"PA-600","type":"Amplificateur","replacement":"PA-600-R2","stock":"AVAILABLE"},
            ])

            alarms.to_excel(DATA_DIR / "dataminer.xlsx", index=False)
            incidents.to_excel(DATA_DIR / "servicenow.xlsx", index=False)
            dma.to_excel(DATA_DIR / "dma.xlsx", index=False)
            diabolo.to_excel(DATA_DIR / "diabolo.xlsx", index=False)
            material.to_excel(DATA_DIR / "material.xlsx", index=False)

    def _read(self, name: str) -> pd.DataFrame:
        with self._lock:
            return pd.read_excel(DATA_DIR / name, keep_default_na=False, dtype=object)

    def _write(self, name: str, df: pd.DataFrame) -> None:
        with self._lock:
            df.to_excel(DATA_DIR / name, index=False)

    def list_alarms(self) -> list[dict[str, Any]]:
        return self._read("dataminer.xlsx").to_dict("records")

    def get_alarm(self, alarm_id: str) -> dict[str, Any]:
        df = self._read("dataminer.xlsx")
        rows = df[df["alarm_id"] == alarm_id]
        if rows.empty:
            raise KeyError(alarm_id)
        return rows.iloc[0].to_dict()

    def update_alarm(self, alarm_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            df = pd.read_excel(DATA_DIR / "dataminer.xlsx", keep_default_na=False, dtype=object)
            idx = df.index[df["alarm_id"] == alarm_id]
            if len(idx) == 0:
                raise KeyError(alarm_id)
            for key, value in changes.items():
                df.loc[idx[0], key] = value
            df.to_excel(DATA_DIR / "dataminer.xlsx", index=False)
        return self.get_alarm(alarm_id)

    def incidents(self) -> list[dict[str, Any]]:
        return self._read("servicenow.xlsx").to_dict("records")

    def create_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            df = pd.read_excel(DATA_DIR / "servicenow.xlsx", keep_default_na=False, dtype=object)
            nums = [int(str(x).replace("INC", "")) for x in df["number"].tolist()]
            number = f"INC{max(nums)+1:07d}"
            row = {"number": number, **payload}
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            df.to_excel(DATA_DIR / "servicenow.xlsx", index=False)
        return row

    def close_incident(self, number: str, resolution_notes: str) -> None:
        with self._lock:
            df = pd.read_excel(DATA_DIR / "servicenow.xlsx", keep_default_na=False, dtype=object)
            idx = df.index[df["number"] == number]
            if len(idx):
                df.loc[idx[0], "state"] = "Closed"
                df.loc[idx[0], "resolution_notes"] = resolution_notes
                df.to_excel(DATA_DIR / "servicenow.xlsx", index=False)

    def active_interventions(self, site: str, equipment: str) -> list[dict[str, Any]]:
        df = self._read("diabolo.xlsx")
        q = df[(df["site"] == site) & (df["equipment"] == equipment) & (df["status"] == "IN_PROGRESS")]
        return q.to_dict("records")

    def dma_rules(self, alarm: str) -> list[dict[str, Any]]:
        df = self._read("dma.xlsx")
        return df[df["alarm"] == alarm].to_dict("records")

    def material_for(self, equipment: str) -> dict[str, Any] | None:
        df = self._read("material.xlsx")
        q = df[df["equipment"] == equipment]
        return None if q.empty else q.iloc[0].to_dict()
