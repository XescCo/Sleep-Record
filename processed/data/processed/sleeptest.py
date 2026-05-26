
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

RAW_DIR = Path(r"C:\Users\franvicens\OneDrive - HBX Group\Documents\8. Portfolio\3. Projects\GithubSleep\Sleep-Record\data\raw\sleep")
OUTPUT   = Path(r"fct_sleep.csv")

records = {}

# ─────────────────────────────────────────
# 1. CARGA + quedarse con el último sleepId
# ─────────────────────────────────────────
for filepath in sorted(RAW_DIR.glob("*.ndjson")):
    with open(filepath) as f:
        for line in f:
            r = json.loads(line)["entryData"]
            records[r["sleepId"]] = r  # mantener el último

print(f"Sleep IDs únicos: {len(records)}")

# ─────────────────────────────────────────
# 2. TRANSFORMACIÓN → construir filas
# ─────────────────────────────────────────
rows = []

for r in records.values():
    bedtime_start = datetime.fromisoformat(r["bedtimeStart"])
    bedtime_end = datetime.fromisoformat(r["bedtimeEnd"])

    fecha_sesion = (bedtime_end - timedelta(days=1)).date()

    # --- métricas base ---
    duracion_total_min = round(r["duration"] / 60, 1)

    deep = r["deepSleepDuration"]
    light = r["lightSleepDuration"]
    rem = r["remSleepDuration"]

    # calcular awake_min
    awake_min = round(
        (r["duration"] - (deep + light + rem)) / 60,
        1
    )

    # --- flags ---
    is_abnormal_session = (
        duracion_total_min < 60 or
        duracion_total_min > 720 or
        (duracion_total_min > 180 and (
            rem == 0 or deep == 0
        )) or
        awake_min > 20 or
        r.get("quality") is None or
        bedtime_end.hour <5
    )

    is_nap = (
        20 <= duracion_total_min <= 120 and
        10 <= bedtime_start.hour <= 20 and
        not is_abnormal_session
    )

    # --- construir row ---
    row = {
        "sleep_id": r.get("sleepId"),
        "fecha_sesion": fecha_sesion,
        "hora_dormirse": bedtime_start.strftime("%H:%M"),
        "hora_despertar": bedtime_end.strftime("%H:%M"),
        "duracion_total_min": duracion_total_min,
        "deep_sleep_min": round(deep / 60, 1),
        "light_sleep_min": round(light / 60, 1),
        "rem_sleep_min": round(rem / 60, 1),
        "wake_after_sleep_onset_min": round(r["wakeAfterSleepOnsetDuration"] / 60, 1),
        "wake_before_offbed_min": round(r["wakeBeforeOffBedDuration"] / 60, 1),
        "awake_event": awake_min > 0,
        "awake_min": awake_min,
        "is_abnormal_session": is_abnormal_session,  # 👈 NUEVO
        "is_nap": is_nap,  # 👈 NUEVO
        "quality": r.get("quality"),
        "avg_hrv": r.get("avgHrv"),
    }

    rows.append(row)

# Crear DataFrame
df = pd.DataFrame(rows).sort_values("fecha_sesion").reset_index(drop=True)

# ─────────────────────────────────────────
# 3. VALIDACIÓN
# ─────────────────────────────────────────
print("\nPreview:")
print(df.head(10).to_string())

print(f"\nRango: {df['fecha_sesion'].min()} → {df['fecha_sesion'].max()}")
print(f"Noches: {len(df)}")

# ─────────────────────────────────────────
# 4. EXPORTAR
# ─────────────────────────────────────────
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)

print(f"\n✅ Guardado en {OUTPUT}")
