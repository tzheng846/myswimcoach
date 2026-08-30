# -*- coding: utf-8 -*-
"""
_home_geom.py — build scratch/_home_geom.json for the marketing home mockup.

Source: scratch/_home_session.json (written by _home_data_probe.py) — the
coach-marked butterfly 25 whose four phase boundaries are all `manual`.

Two rules this file enforces, both from the 2026-08-29 discussion:
  1. Trace GEOMETRY is real and unmodified. Shapes come straight from
     velocity_profile at the session's own sample rate (89.99 Hz, never 100).
  2. Printed metric VALUES are deterministically perturbed, so no real
     athlete number is published. Nothing on the page may be labelled
     "real data" as a result.
"""
import json
import math

S = json.load(open('scratch/_home_session.json', encoding='utf-8'))

VEL = [float(v) for v in S['velocity_profile']]
FS = float(S['sample_rate_hz'])                      # 89.9928..., NOT 100
PH = S['metrics_json']['phases']
B = PH['boundaries']
CYCLES = S['metrics_json']['cycles']

VMAX = max(VEL)
N = len(VEL)

WINDOWS = {
    'start': (B['dive_start_s'], B['underwater_start_s']),
    'uw':    (B['underwater_start_s'], B['stroke_start_s']),
    'swim':  (B['stroke_start_s'], B['finish_s']),
}

# ---------------------------------------------------------------- perturbation
# Fixed multiplicative offsets, hand-picked per metric key. Deterministic (no
# RNG) so the mockup is reproducible and reviewable.
JITTER = {
    'peak_vel': 1.043, 'time_to_peak_vel': 0.951, 'glide_distance': 1.062,
    'break_into_kick_vel': 0.968, 'glide_duration': 1.037, 'glide_avg_speed': 0.972,
    'max_accel': 0.966,
    'kick_count': 1.0, 'kick_tempo': 0.958, 'dist_per_kick': 1.055,
    'uw_avg_speed': 1.031, 'per_kick_decay': 0.944, 'kick_consistency': 1.048,
    'ivv': 0.963, 'dead_spot_timing': 1.071, 'breakout_vel': 1.028,
    'sr_dps_coupling': 0.949, 'breakout_vs_steady': 1.034,
    'splits_20m': 0.972, 'accel_asymmetry': 0.955,
}


def val(phase, key):
    v = PH[phase][key]['value']
    return None if v is None else v * JITTER.get(key, 1.0)


# ------------------------------------------------------------------- polylines
def slice_poly(t0, t1, pad_frac, w, h, pad_min=0.40):
    """Velocity slice [t0,t1] with context padding, mapped into a w x h box.

    Returns (polyline, x_of_t0, x_of_t1) so the caller can tint the in-phase
    span and leave the padding grey. y is scaled by the WHOLE swim's VMAX so
    the three phase cards stay comparable to each other.
    """
    pad = max((t1 - t0) * pad_frac, pad_min)
    a = max(0.0, t0 - pad)
    b = min((N - 1) / FS, t1 + pad)
    i0, i1 = int(a * FS), int(b * FS)
    seg = VEL[i0:i1 + 1]
    span = max(1, len(seg) - 1)
    pts = ' '.join(
        '%.1f,%.1f' % (i / span * w, h - (v / VMAX) * (h - 6) - 3)
        for i, v in enumerate(seg)
    )
    return pts, (t0 - a) / (b - a) * w, (t1 - a) / (b - a) * w


geom = {'phase_slices': {}}
for k, (t0, t1) in WINDOWS.items():
    pts, x0, x1 = slice_poly(t0, t1, 0.22, 300.0, 92.0)
    geom['phase_slices'][k] = {
        'poly': pts, 'x0': round(x0, 1), 'x1': round(x1, 1),
        'dur': round(t1 - t0, 2),
    }

# ------------------------------------------------------- whole swim, banded
# One chart, the entire recorded lap, with each phase window highlighted in
# place. Replaces the three separate per-phase slices.
WW, WH = 900.0, 250.0
T_END = (N - 1) / FS


def _x(t):
    return t / T_END * WW


geom['whole'] = {
    'poly': ' '.join('%.1f,%.1f' % (i / (N - 1) * WW, WH - (v / VMAX) * (WH - 34) - 8)
                     for i, v in enumerate(VEL)),
    'bands': {k: {'x': round(_x(t0), 1), 'w': round(_x(t1) - _x(t0), 1),
                  'mid': round(_x((t0 + t1) / 2), 1)}
              for k, (t0, t1) in WINDOWS.items()},
    'tail': {'x': round(_x(B['finish_s']), 1),
             'w': round(WW - _x(B['finish_s']), 1)},
    'vmax': round(VMAX, 2),
    'end': round(T_END, 1),
}

# ---------------------------------------------------------------- cycle traces
# The five real stroke cycles, each drawn from its own start_idx..end_idx on a
# shared axis. Longest cycle sets the x extent so durations stay honest.
longest = max(c['end_idx'] - c['start_idx'] for c in CYCLES)
CW, CH = 320.0, 130.0
traces = []
for c in CYCLES:
    seg = VEL[c['start_idx']:c['end_idx'] + 1]
    pts = ' '.join(
        '%.1f,%.1f' % (i / longest * CW, CH - (v / VMAX) * (CH - 10) - 5)
        for i, v in enumerate(seg)
    )
    traces.append({'n': c['cycle_num'] + 1, 'poly': pts,
                   'dur': round(c['duration_s'], 2)})

# Pick the cycle whose duration is furthest from the median as the "odd" one.
durs = sorted(c['duration_s'] for c in CYCLES)
med = durs[len(durs) // 2]
odd = max(CYCLES, key=lambda c: abs(c['duration_s'] - med))
geom['cycles'] = traces
geom['odd_cycle'] = odd['cycle_num'] + 1
geom['cycle_dur_spread'] = [round(durs[0], 2), round(durs[-1], 2)]

# --------------------------------------------------------------------- radars
# Four axes per phase.
#   `r`    today's radius, from the REAL (perturbed) value mapped through a
#          hand-set display range (lo, hi). hi < lo means lower is better, so
#          the axis reads outward-is-good like every other one.
#   `ring` the "usual range" radius for that axis. DRAWN, not computed: this
#          athlete has only two other same-stroke swims, far short of the five
#          the product actually uses, so a real ring would misrepresent the
#          baseline. Ring values are irregular on purpose, because a real
#          usual-range polygon is not a circle.
RADAR = {
    'start': [
        ('Peak speed',       'start', 'peak_vel',            1.60,  2.75, 0.70),
        ('Time to peak',     'start', 'time_to_peak_vel',    0.26,  0.05, 0.66),
        ('Push acceleration', 'start', 'max_accel',         12.00, 30.00, 0.74),
        ('Glide distance',   'start', 'glide_distance',      0.45,  1.70, 0.62),
        ('Into first kick',  'start', 'break_into_kick_vel', 0.75,  1.85, 0.58),
    ],
    'uw': [
        ('Kick count',      'underwater', 'kick_count',      6.00, 16.00, 0.62),
        ('Kick tempo',      'underwater', 'kick_tempo',      1.75,  2.45, 0.66),
        ('Distance / kick', 'underwater', 'dist_per_kick',   0.50,  0.92, 0.70),
        ('Speed held',      'underwater', 'uw_avg_speed',    1.05,  1.75, 0.64),
        ('Kick evenness',   'underwater', 'kick_consistency', 0.26, 0.06, 0.68),
    ],
    'swim': [
        ('Breakout speed', 'swim', 'breakout_vel',     1.30, 1.72, 0.64),
        ('Speed evenness', 'swim', 'ivv',              0.44, 0.26, 0.60),
        ('Pace held late', 'swim', 'splits_20m',       1.26, 1.52, 0.66),
        ('Drive vs coast', 'swim', 'dead_spot_timing', 0.29, 0.12, 0.62),
        ('Stroke balance', 'swim', 'accel_asymmetry',  0.60, 0.95, 0.58),
    ],
}

radars = {}
for card, axes in RADAR.items():
    out = []
    for label, phase, key, lo, hi, ring in axes:
        v = val(phase, key)
        norm = 0.5 if v is None else (v - lo) / (hi - lo)
        norm = max(0.0, min(1.0, norm))
        out.append({'label': label,
                    'r': round(0.30 + 0.62 * norm, 3),
                    'ring': ring,
                    'disp': None if v is None else round(v, 2)})
    radars[card] = out
geom['radars'] = radars

# Raw perturbed numbers the copy quotes, so the template never hard-codes one.
geom['numbers'] = {
    'kick_count': int(round(val('underwater', 'kick_count'))),
    'uw_dist_share': round(PH['whole']['phase_dist_budget_underwater']['value'] * 0.981),
    'n_cycles': len(CYCLES),
    'swim_dur': round(WINDOWS['swim'][1] - WINDOWS['swim'][0], 1),
    'total_dur': round(B['finish_s'] - B['dive_start_s'], 1),
}

json.dump(geom, open('scratch/_home_geom.json', 'w', encoding='utf-8'), indent=1)
print('phase slices :', {k: v['dur'] for k, v in geom['phase_slices'].items()})
print('cycles       :', len(traces), 'odd =', geom['odd_cycle'],
      'spread', geom['cycle_dur_spread'])
print('numbers      :', geom['numbers'])
for k, v in radars.items():
    print(f'radar {k:<6}:', [(a['label'], a['r'], a['disp']) for a in v])
