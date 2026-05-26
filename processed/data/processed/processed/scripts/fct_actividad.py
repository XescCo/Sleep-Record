import json
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# ─────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────
RAW_DIR = Path(r"C:\Users\franvicens\OneDrive - HBX Group\Documents\8. Portfolio\3. Projects\GithubSleep\Sleep-Record\data\raw\activity")
OUTPUT   = Path("fct_actividad.csv")

# Umbral para considerar ruido en pasos
STEP_THRESHOLD = 50

# ─────────────────────────────────────────
# 1. CARGA
# ─────────────────────────────────────────
records = []

for filepath in sorted(RAW_DIR.glob("*.ndjson")):
    with open(filepath) as f:
        for line in f:
            r = json.loads(line)

            ts = datetime.fromisoformat(r['timestamp'])

            # Regla 05:00
            if ts.hour < 5:
                fecha_sesion = (ts - timedelta(days=1)).date()
            else:
                fecha_sesion = ts.date()

            entry = r.get('entryData', {})

            records.append({
                'fecha_sesion': fecha_sesion,
                'ts':           ts,
                'steps':        entry.get('stepCount', 0),
                'energy':       entry.get('energyConsumption', 0),
                'hr':           entry.get('hr', None) * 60 if entry.get('hr') is not None else None  # ✅ HR ajustado
            })

print(f"Registros raw cargados: {len(records)}")

# ─────────────────────────────────────────
# 2. AGREGACIÓN
# ─────────────────────────────────────────
by_date = defaultdict(list)

for r in records:
    by_date[r['fecha_sesion']].append(r)

rows = []

for fecha, day_records in sorted(by_date.items()):

    # HR limpio
    hr_values = [r['hr'] for r in day_records if r['hr'] is not None]

    # Eventos con pasos
    step_events = [r for r in day_records if r['steps'] > 0]

    # --- lógica de último paso robusto ---
    last_step = None

    if len(step_events) == 1:
        # solo uno → lo usamos directamente
        last_step = step_events[0]

    elif len(step_events) > 1:
        # ordenar por tiempo por seguridad
        step_events_sorted = sorted(step_events, key=lambda x: x['ts'])

        last_candidate = step_events_sorted[-1]
        prev_candidate = step_events_sorted[-2]

        # comprobar si el último parece ruido
        is_small = last_candidate['steps'] < STEP_THRESHOLD

        # aislado = el anterior también tenía pocos pasos (o gap mental)
        is_isolated = prev_candidate['steps'] == 0 if prev_candidate else True

        if is_small:
            # usamos el penúltimo
            last_step = prev_candidate
        else:
            last_step = last_candidate

    # primer paso (más simple)
    first_step = min(step_events, key=lambda x: x['ts']) if step_events else None

    rows.append({
        'fecha_sesion':     fecha,
        'pasos_total':      round(sum(r['steps'] for r in day_records)),
        'energia_total':    round(sum(r['energy'] for r in day_records), 1),
        'hr_media':         round(sum(hr_values) / len(hr_values), 2) if hr_values else None,
        'hr_max':           round(max(hr_values), 2) if hr_values else None,
        'hr_min':           round(min(hr_values), 2) if hr_values else None,
        'hora_primer_paso': first_step['ts'].strftime('%H:%M') if first_step else None,
        'hora_ultimo_paso': last_step['ts'].strftime('%H:%M') if last_step else None,
    })

# ─────────────────────────────────────────
# 3. DATAFRAME
# ─────────────────────────────────────────
df = pd.DataFrame(rows).sort_values("fecha_sesion").reset_index(drop=True)

# ─────────────────────────────────────────
# 4. VALIDACIÓN
# ─────────────────────────────────────────
dupes = df[df.duplicated("fecha_sesion", keep=False)]

if not dupes.empty:
    print(f"⚠️ Fechas duplicadas:\n{dupes[['fecha_sesion']]}")
else:
    print("✅ Sin fechas duplicadas")

print(f"Rango: {df['fecha_sesion'].min()} → {df['fecha_sesion'].max()}")
print(f"Días procesados: {len(df)}")

print("\nPreview:")
print(df.head(10).to_string())

# ─────────────────────────────────────────
# 5. EXPORT
# ─────────────────────────────────────────
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT, index=False)

print(f"\n✅ Guardado en {OUTPUT}")

