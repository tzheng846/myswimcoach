function MetricItem({ label, value, unit }) {
  return (
    <div className="flex-1 text-center">
      <p className="text-[11px] uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-0.5 font-mono text-2xl font-bold text-ink">
        {value ?? "--"}
      </p>
      {unit ? <p className="text-[11px] text-muted">{unit}</p> : null}
    </div>
  );
}

function SectionCard({ title, children }) {
  return (
    <div className="rounded-xl border border-navy/50 bg-surface p-4">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-muted">
        {title}
      </p>
      {children}
    </div>
  );
}

export function SessionSummaryCard({ session, unit }) {
  const lapRaw = session?.lap_time_s;
  const lapFmt =
    lapRaw != null
      ? lapRaw >= 60
        ? `${Math.floor(lapRaw / 60)}:${String(Math.round(lapRaw % 60)).padStart(2, "0")}`
        : lapRaw.toFixed(1)
      : "--";
  const factor = unit === "imperial" ? 1.09361 : 1;
  const speed =
    session?.mean_vel_ms != null
      ? (session.mean_vel_ms * factor).toFixed(2)
      : "--";
  return (
    <SectionCard title="Session">
      <div className="flex">
        <MetricItem label="Lap Time" value={lapFmt} unit="s" />
        <MetricItem
          label="Rate"
          value={session?.stroke_rate_spm?.toFixed(1)}
          unit="SPM"
        />
        <MetricItem
          label="Speed"
          value={speed}
          unit={unit === "imperial" ? "yd/s" : "m/s"}
        />
      </div>
    </SectionCard>
  );
}

// Full metric breakdown — ports the iOS ReportCardScreen sections.
export default function MetricGrid({ metrics, unit }) {
  const s = metrics?.session ?? {};
  const ip = metrics?.initial_phase ?? {};
  const factor = unit === "imperial" ? 1.09361 : 1;
  const distUnit = unit === "imperial" ? "yd" : "m";
  const velUnit = unit === "imperial" ? "yd/s" : "m/s";
  const fmtDist = (v) => (v != null ? (v * factor).toFixed(1) : null);
  const fmtVel = (v) => (v != null ? (v * factor).toFixed(2) : null);
  const efficiencyUnreliable = (s.cv_isi ?? 0) > 0.8;

  return (
    <div className="space-y-3">
      <SectionCard title="Start Phase">
        {ip.dive_detected ? (
          <div className="flex">
            <MetricItem
              label="Dive Duration"
              value={ip.dive_duration_s?.toFixed(2)}
              unit="s"
            />
            <MetricItem
              label="Pulldown Peak"
              value={fmtVel(ip.pulldown_peak_vel_ms)}
              unit={velUnit}
            />
            <MetricItem
              label="Pulldown Time"
              value={ip.pulldown_duration_s?.toFixed(2)}
              unit="s"
            />
          </div>
        ) : (
          <p className="text-sm italic text-muted">
            {ip.pulldown_detected
              ? "Pulldown detected — no dive surge"
              : "Wall start — no dive or pulldown"}
          </p>
        )}
      </SectionCard>

      <SectionCard title="Session">
        <div className="flex">
          <MetricItem label="Lap Time" value={s.lap_time_s?.toFixed(2)} unit="s" />
          <MetricItem
            label="Distance"
            value={fmtDist(s.total_dist_m)}
            unit={distUnit}
          />
          <MetricItem
            label="Active Rate"
            value={s.stroke_rate_spm?.toFixed(1)}
            unit="SPM"
          />
        </div>
        <div className="mt-4 flex">
          <MetricItem label="Strokes" value={s.stroke_count} unit="" />
          <MetricItem
            label="Avg Speed"
            value={fmtVel(s.mean_vel_ms)}
            unit={velUnit}
          />
          <MetricItem
            label="Max Speed"
            value={fmtVel(s.max_vel_ms)}
            unit={velUnit}
          />
        </div>
      </SectionCard>

      <SectionCard title="Efficiency">
        {efficiencyUnreliable ? (
          <p className="text-sm italic leading-relaxed text-warning-2">
            Stroke detection may be unreliable for this session. Check
            recording conditions or technique consistency.
          </p>
        ) : (
          <>
            <div className="flex">
              <MetricItem
                label="Dist/Stroke"
                value={fmtDist(s.mean_dps_m)}
                unit={distUnit}
              />
              <MetricItem
                label="Impulse"
                value={fmtDist(s.mean_impulse_m)}
                unit={distUnit}
              />
              <MetricItem
                label="Coast"
                value={
                  s.mean_coast_fraction != null
                    ? (s.mean_coast_fraction * 100).toFixed(1)
                    : null
                }
                unit="%"
              />
            </div>
            <div className="mt-4 flex">
              <MetricItem
                label="ISI CV"
                value={s.cv_isi != null ? (s.cv_isi * 100).toFixed(1) : null}
                unit="%"
              />
              <MetricItem
                label="Arm Peak CV"
                value={
                  s.cv_arm_peak_vel != null
                    ? (s.cv_arm_peak_vel * 100).toFixed(1)
                    : null
                }
                unit="%"
              />
              <MetricItem
                label="Fatigue"
                value={s.fatigue_index_pct?.toFixed(1)}
                unit="%"
              />
            </div>
          </>
        )}
      </SectionCard>
    </div>
  );
}
