
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
RAW_DIR = Path(r"C:\Users\franvicens\OneDrive - HBX Group\Documents\8. Portfolio\3. Projects\GithubSleep\Sleep-Record\data\raw\sleep")
OUTPUT   = Path(r"fct_sleep.csv")

# ─────────────────────────────────────────
# 1. CARGA — todos los ficheros .ndjson
# ─────────────────────────────────────────
records = []
for filepath in sorted(RAW_DIR.glob("*.ndjson")):
    with open(filepath) as f:
        for line in f:
            r = json.loads(line)
            records.append(r["entryData"])

print(f"Registros raw cargados: {len(records)}")

# ─────────────────────────────────────────
# 2. DEDUPLICACIÓN por sleepId
# ─────────────────────────────────────────
seen = set()
unique = []
for r in records:
    if r["sleepId"] not in seen:
        seen.add(r["sleepId"])
        unique.append(r)

print(f"Tras deduplicar: {len(unique)}")

# ─────────────────────────────────────────
# 3. FILTRO — excluir siestas
# ─────────────────────────────────────────
def is_night_session(r):
    start = datetime.fromisoformat(r["bedtimeStart"])
    duration_min = r["duration"] / 60
    return (start.hour >= 21 or start.hour < 3) and duration_min > 120

nights = [r for r in unique if is_night_session(r)]

print(f"Noches válidas: {len(nights)}")

# ─────────────────────────────────────────
# 4. TRANSFORMACIÓN
# ─────────────────────────────────────────
def build_row(r):
    bedtime_start = datetime.fromisoformat(r["bedtimeStart"])
    bedtime_end = datetime.fromisoformat(r["bedtimeEnd"])

    # fecha_sesion = día en que te acuestas (equivalente a end - 1)
    fecha_sesion = (bedtime_end - timedelta(days=1)).date()

    return {
        "fecha_sesion": fecha_sesion,
        "hora_dormirse": bedtime_start.strftime("%H:%M"),
        "hora_despertar": bedtime_end.strftime("%H:%M"),
        "duracion_total_min": round(r["duration"] / 60, 1),
        "deep_sleep_min": round(r["deepSleepDuration"] / 60, 1),
        "light_sleep_min": round(r["lightSleepDuration"] / 60, 1),
        "rem_sleep_min": round(r["remSleepDuration"] / 60, 1),
        "wake_after_sleep_onset_min": round(r["wakeAfterSleepOnsetDuration"] / 60, 1),
        "wake_before_offbed_min": round(r["wakeBeforeOffBedDuration"] / 60, 1),
        "quality": r.get("quality"),
        "avg_hrv": r.get("avgHrv"),
    }

# ✅ ESTO estaba mal indentado antes
rows = [build_row(r) for r in nights]
df = pd.DataFrame(rows).sort_values("fecha_sesion").reset_index(drop=True)

# ─────────────────────────────────────────
# 5. VALIDACIÓN básica
# ─────────────────────────────────────────
dupes = df[df.duplicated("fecha_sesion", keep=False)]

if not dupes.empty:
    print(f"⚠️  Fechas duplicadas:\n{dupes[['fecha_sesion','hora_dormirse','hora_despertar']]}")
else:
    print("✅ Sin fechas duplicadas")

print(f"Rango: {df['fecha_sesion'].min()} → {df['fecha_sesion'].max()}")
print(f"Noches procesadas: {len(df)}")

# ─────────────────────────────────────────
# 6. EXPORTAR
# ─────────────────────────────────────────
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)

print(f"✅ Guardado en {OUTPUT}")
print(df.head(10).to_string())

