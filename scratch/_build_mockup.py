# -*- coding: utf-8 -*-
"""
Builds scratch/website-home-mockup.html.

Trace geometry comes from scratch/_home_geom.json (one real coach-marked
butterfly 25). Printed metric values there are already perturbed. The usual
range ring on each radar and the six comparison strips are drawn, not measured.
"""
import json
import math

G = json.load(open('scratch/_home_geom.json', encoding='utf-8'))

PHASE_COLOR = {'start': '#f2b134', 'uw': '#2196f3', 'swim': '#a970ff'}
VAL = {'good': '#2f9e63', 'bad': '#c9503f', 'flat': '#6e5a78'}


# ------------------------------------------------------------- phase trace
def slice_svg(key, label):
    """Real velocity slice. In-phase span tinted, context padding left grey."""
    s = G['phase_slices'][key]
    c = PHASE_COLOR[key]
    return (
        '<svg viewBox="0 0 300 92" style="width:100%%;height:auto;display:block" aria-hidden="true">\n'
        '            <rect x="%.1f" y="0" width="%.1f" height="92" fill="%s" opacity=".16"/>\n'
        '            <polyline points="%s" fill="none" stroke="#2c0735" stroke-width="1.7" '
        'stroke-linejoin="round" stroke-linecap="round"/>\n'
        '          </svg>\n'
        '          <p class="cap">%s</p>'
        % (s['x0'], s['x1'] - s['x0'], c, s['poly'], label % s['dur'])
    )


# ------------------------------------------------------------------ radar
def radar_svg(key):
    """N axis radar. Today polygon is real; the usual range ring is drawn.

    Axis count comes from the data, so adding or removing a metric in
    _home_geom.py needs no change here.
    """
    axes = G['radars'][key]
    n = len(axes)
    c = PHASE_COLOR[key]
    # viewBox is wider than the plot so the outer labels sit clear of the
    # card edge instead of clipping.
    cx, cy, R = 150.0, 108.0, 66.0
    ang = [-90 + i * (360.0 / n) for i in range(n)]

    def pt(i, r):
        a = math.radians(ang[i])
        return cx + math.cos(a) * R * r, cy + math.sin(a) * R * r

    web = []
    for ring in (0.35, 0.7, 1.0):
        pts = ' '.join('%.1f,%.1f' % pt(i, ring) for i in range(n))
        web.append('<polygon points="%s" fill="none" stroke="#e8e4f2" stroke-width="1"/>' % pts)
    for i in range(n):
        x, y = pt(i, 1.0)
        web.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e8e4f2" '
                   'stroke-width="1"/>' % (cx, cy, x, y))

    usual_o = ' '.join('%.1f,%.1f' % pt(i, a['ring'] + 0.085) for i, a in enumerate(axes))
    usual_i = ' '.join('%.1f,%.1f' % pt(i, max(0.05, a['ring'] - 0.085)) for i, a in enumerate(axes))
    today = ' '.join('%.1f,%.1f' % pt(i, a['r']) for i, a in enumerate(axes))

    dots = ''.join('<circle cx="%.1f" cy="%.1f" r="3.4" fill="%s" stroke="#fff" '
                   'stroke-width="1.2"/>' % (pt(i, a['r']) + (c,))
                   for i, a in enumerate(axes))

    # Anchor each label by which side of the circle its axis points to.
    labels = []
    for i, a in enumerate(axes):
        x, y = pt(i, 1.0)
        dx, dy = math.cos(math.radians(ang[i])), math.sin(math.radians(ang[i]))
        anchor = 'middle' if abs(dx) < 0.25 else ('start' if dx > 0 else 'end')
        x += 8 * dx
        y += 13 * dy + (0 if abs(dy) < 0.25 else 3)
        labels.append('<text x="%.1f" y="%.1f" fill="#6e5a78" font-size="10.5" '
                      'text-anchor="%s">%s</text>' % (x, y, anchor, a['label']))

    return (
        '<svg viewBox="0 0 300 214" style="width:100%%;height:auto;display:block" aria-hidden="true">\n'
        '            %s\n'
        '            <polygon points="%s" fill="#9b8ba6" opacity=".16"/>\n'
        '            <polygon points="%s" fill="#fbfbfe"/>\n'
        '            <polygon points="%s" fill="none" stroke="#9b8ba6" stroke-width="1" '
        'stroke-dasharray="3 3"/>\n'
        '            <polygon points="%s" fill="%s" opacity=".24" stroke="%s" stroke-width="2.4" '
        'stroke-linejoin="round"/>\n'
        '            %s\n'
        '            %s\n'
        '          </svg>'
        % ('\n            '.join(web), usual_o, usual_i, usual_o, today, c, c, dots,
           '\n            '.join(labels))
    )


def whole_svg():
    """The entire recorded lap on one chart, each phase window highlighted."""
    w = G['whole']
    b = w['bands']
    bands = ''.join(
        '<rect x="%.1f" y="0" width="%.1f" height="250" fill="%s" opacity=".15"/>'
        % (b[k]['x'], b[k]['w'], PHASE_COLOR[k]) for k in ('start', 'uw', 'swim'))
    bands += ('<rect x="%.1f" y="0" width="%.1f" height="250" fill="#9b8ba6" opacity=".07"/>'
              % (w['tail']['x'], w['tail']['w']))
    ticks = ''.join(
        '<line x1="%.1f" y1="0" x2="%.1f" y2="250" stroke="%s" stroke-width="1.2" '
        'opacity=".55"/>' % (b[k]['x'], b[k]['x'], PHASE_COLOR[k])
        for k in ('start', 'uw', 'swim'))
    # The Start window is only ~0.6 s of a ~20 s lap, so its band is far
    # narrower than the word START. Shrink the label rather than let it spill
    # across the neighbouring phases.
    names = ''.join(
        '<text x="%.1f" y="20" text-anchor="middle" font-size="%s" letter-spacing="%s">%s</text>'
        % (b[k]['mid'], 9 if b[k]['w'] < 70 else 11.5, 0.4 if b[k]['w'] < 70 else 1.5, lab)
        for k, lab in (('start', 'START'), ('uw', 'UNDERWATER'), ('swim', 'SWIMMING')))
    return (
        '<svg viewBox="0 0 900 250" style="width:100%%;height:auto;display:block" aria-hidden="true">\n'
          '          %s\n'
          '          %s\n'
          '          <polyline points="%s" fill="none" stroke="#2c0735" stroke-width="1.9" '
          'stroke-linejoin="round" stroke-linecap="round"/>\n'
          '          <g font-weight="700" fill="#6e5a78">%s</g>\n'
          '          <text x="4" y="20" fill="#9b8ba6" font-size="11">m/s</text>\n'
          '          <text x="896" y="20" fill="#9b8ba6" font-size="11" text-anchor="end">%s s</text>\n'
          '        </svg>' % (bands, ticks, w['poly'], names, w['end'])
    )


# ------------------------------------------------------------ cycle overlay
odd = G['odd_cycle']
trace_svg = '\n'.join(
    '      <polyline points="%s" fill="none" stroke="%s" stroke-width="%s" '
    'stroke-linejoin="round" stroke-linecap="round" opacity="%s"/>'
    % (t['poly'], '#4e148c' if t['n'] == odd else '#b9aecf',
       2.2 if t['n'] == odd else 1.3, 1 if t['n'] == odd else 0.75)
    for t in G['cycles']
)

# ------------------------------------------------------------------ strips
# Illustrative, but internally coherent: an alert fires ONLY when today falls
# outside the usual range. Inside the band is "normal" and is not an alert, so
# the grey rows are excluded from the count above. Asserted below.
#                             label                  today  lo  hi  med  valence
strips = [
    ('Peak speed off the block',   89, 62, 84, 73, 'good'),
    ('Underwater kick count',      41, 55, 78, 66, 'bad'),
    ('Breakout distance',          63, 52, 76, 64, 'flat'),
    ('Distance per stroke',        71, 58, 80, 69, 'flat'),
    ('Speed lost across the lap',  88, 44, 70, 57, 'bad'),
    ('Coast fraction',             52, 46, 72, 59, 'flat'),
]
for _lab, _today, _lo, _hi, _med, _v in strips:
    inside = _lo <= _today <= _hi
    assert inside == (_v == 'flat'), (
        '%s: valence %r contradicts the band. An alert must be OUTSIDE the '
        'usual range and a normal row must be inside it.' % (_lab, _v))
rows = []
for label, today, lo, hi, med, val in strips:
    rows.append(
        '        <div class="strip">\n'
        '          <div class="strip-label">%s</div>\n'
        '          <svg viewBox="0 0 200 18" class="strip-svg" aria-hidden="true">\n'
        '            <rect x="0" y="7" width="200" height="4" rx="2" fill="#ece7f5"/>\n'
        '            <rect x="%s" y="4" width="%s" height="10" rx="5" fill="#d9d2ec"/>\n'
        '            <rect x="%s" y="2" width="1.6" height="14" fill="#9b8ba6"/>\n'
        '            <circle cx="%s" cy="9" r="5.4" fill="%s"/>\n'
        '            <circle cx="%s" cy="9" r="5.4" fill="none" stroke="#ffffff" stroke-width="1.6"/>\n'
        '          </svg>\n'
        '        </div>'
        % (label, lo * 2, (hi - lo) * 2, med * 2 - 0.6, today * 2, VAL[val], today * 2)
    )
strip_svg = '\n'.join(rows)

n_bad = sum(1 for s in strips if s[5] == 'bad')
n_good = sum(1 for s in strips if s[5] == 'good')
n_normal = sum(1 for s in strips if s[5] == 'flat')
n_alerts = n_bad + n_good           # normals are NOT alerts

# ------------------------------------------------------------------- build
tpl = open('scratch/_mockup_template.html', encoding='utf-8').read()
html = (tpl
        .replace('%%WHOLE%%', whole_svg())
        .replace('%%RADAR_START%%', radar_svg('start'))
        .replace('%%RADAR_UW%%', radar_svg('uw'))
        .replace('%%RADAR_SWIM%%', radar_svg('swim'))
        .replace('%%STRIPS%%', strip_svg)
        .replace('%%TRACES%%', trace_svg)
        .replace('%%ALERT_N%%', str(n_alerts))
        .replace('%%ALERT_BAD%%', str(n_bad))
        .replace('%%ALERT_GOOD%%', str(n_good))
        .replace('%%N_NORMAL%%', str(n_normal))
        .replace('%%N_CYCLES%%', str(G['numbers']['n_cycles']))
        .replace('%%ODD%%', str(odd)))

assert '%%' not in html, 'unfilled placeholder'
assert '—' not in html, 'EM DASH FOUND'
assert '–' not in html, 'EN DASH FOUND'
assert 'GoPro' not in html and 'gopro' not in html.lower(), 'BRAND NAME FOUND'
assert 'REAL DATA' not in html, 'page must not claim real data while values are perturbed'
assert 'Chantee' not in html, 'athlete name leaked'
assert 'changed (unclear)' not in html, 'neutral alert bucket should be gone'
open('scratch/website-home-mockup.html', 'w', encoding='utf-8').write(html)
print('written %d chars' % len(html))
print('alert line: %d alerts (%d worse / %d better); %d normal rows excluded'
      % (n_alerts, n_bad, n_good, n_normal))
print('radar axes: %s' % {k: len(v) for k, v in G['radars'].items()})
print('cycles %d, odd = %d' % (len(G['cycles']), odd))
print('assertions passed: no em/en dash, no brand name, no real-data claim, no athlete name')
