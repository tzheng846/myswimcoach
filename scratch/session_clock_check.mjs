// Phase 86-02 check for the mobile app's session-clock math.
//
// The mobile tree has no test runner (84-03 G28), so `src/lib/sessionClock.js` was written with ZERO
// imports specifically to be checkable from here. It answers one question — what absolute UTC instant
// was encoder sample #0? — and it is the only bridge between the ESP32's boot-relative micros() and
// wall time. Before 86-02 the phone assumed the inbound BLE leg was zero, biasing every session start
// LATE by one one-way flight time; this module measures that leg instead and corrects for it.
//
// Also guards two cross-repo facts that nothing can enforce at runtime:
//   • the plausibility window (_EPOCH_MS_FLOOR / _EPOCH_MS_FUTURE_SLACK_MS) is duplicated in api.py
//     and in the mobile module. A value outside the server's window is dropped inside the handler
//     with a print() the phone never sees — no 4xx, no symptom, and NO BACKFILL IS POSSIBLE, so the
//     session's absolute start is gone permanently. This parses api.py and fails on drift.
//   • RecordScreen must send session_start_utc_ms through Math.round. api.py declares it Optional[int],
//     so a fractional string 422s the request BEFORE the handler runs — losing the whole swim, not
//     just the clock annotation.
//
// Run: node scratch/session_clock_check.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..");
const mobile = path.resolve(repo, "..", "swimnetics-mobile");
const modulePath = path.resolve(mobile, "src", "lib", "sessionClock.js");

// swimnetics-mobile/package.json has no `"type": "module"`, so Node would treat this .js as CJS and
// choke on its `export` statements. Loading the source through a data: URL imports it AS an ES module
// without touching the mobile tree — safe precisely because the module has no imports of its own.
const src = fs.readFileSync(modulePath, "utf8");
const mod = await import(`data:text/javascript,${encodeURIComponent(src)}`);
const {
  META_PROBE_COUNT, META_PROBE_TIMEOUT_MS, META_PROBE_BUDGET_MS,
  EPOCH_MS_FLOOR, EPOCH_MS_FUTURE_SLACK_MS,
  elapsedUs, probeRttMs, pickBestProbe, sessionStartUtcMsFrom, syncErrorMsFrom,
  clockOffsetMs, isPlausibleEpochMs,
} = mod;

let pass = 0;
let fail = 0;
const check = (name, ok, extra = "") => {
  if (ok) {
    pass++;
    console.log(`  PASS  ${name}${extra ? "  " + extra : ""}`);
  } else {
    fail++;
    console.log(`  FAIL  ${name}${extra ? "  " + extra : ""}`);
  }
};

// ---------- the module has no imports (that is what makes this file possible) ----------

check("sessionClock.js has zero imports", !/^\s*(import\s|.*\brequire\()/m.test(src));

// ---------- elapsedUs: the device clock is micros(), which wraps at 2^32 ----------

check("elapsedUs, ordinary case", elapsedUs(5_000_000, 1_000_000) === 4_000_000,
      String(elapsedUs(5_000_000, 1_000_000)));
{
  // deviceNow has wrapped past 2^32 while sessionStart sits just below it: 1 s really did elapse.
  const start = 2 ** 32 - 500_000;
  const now = 500_000;
  check("elapsedUs handles the u32 wrap", elapsedUs(now, start) === 1_000_000,
        String(elapsedUs(now, start)));
}

// ---------- pickBestProbe: the MINIMUM RTT, never the first, last, or mean ----------

{
  const probe = (tSendMs, rtt, tag) => ({ tSendMs, tRecvMs: tSendMs + rtt, tag,
                                          sessionStartUs: 1_000_000, deviceNowUs: 5_000_000 });
  const probes = [probe(1000, 80, "first"), probe(2000, 22, "best"), probe(3000, 55, "last")];
  const best = pickBestProbe(probes);
  check("pickBestProbe returns the minimum-RTT entry", best?.tag === "best", `got ${best?.tag}`);
  check("pickBestProbe is not the first", best?.tag !== "first");
  check("pickBestProbe is not the last", best?.tag !== "last");
  check("probeRttMs of the winner is the minimum", probeRttMs(best) === 22, String(probeRttMs(best)));
  check("pickBestProbe([]) is null", pickBestProbe([]) === null);
  check("pickBestProbe(null) is null", pickBestProbe(null) === null);
  // "all probes failed" reaches the caller as an empty array — every timed-out probe is skipped.
  check("pickBestProbe on an all-null array is null", pickBestProbe([null, null]) === null);
}

// ---------- the correction itself: earlier than the old formula, by exactly rtt/2 ----------

{
  const rtt = 60;
  const p = { tSendMs: 1_756_500_000_000, tRecvMs: 1_756_500_000_000 + rtt,
              sessionStartUs: 1_000_000, deviceNowUs: 31_000_000 };  // 30 s of encoder time
  const expected = (p.tRecvMs - rtt / 2) - 30_000;
  const got = sessionStartUtcMsFrom(p);
  check("sessionStartUtcMsFrom matches the hand-computed fixture", got === expected,
        `got=${got} expected=${expected}`);

  // AC-1's regression is the whole point: assert the DIRECTION, not just the number.
  const uncorrected = p.tRecvMs - elapsedUs(p.deviceNowUs, p.sessionStartUs) / 1000;
  check("corrected start is EARLIER than the pre-86-02 uncorrected one", got < uncorrected,
        `corrected=${got} uncorrected=${uncorrected}`);
  check("...earlier by exactly rtt/2", uncorrected - got === rtt / 2, String(uncorrected - got));
  check("syncErrorMsFrom is that same rtt/2", syncErrorMsFrom(p) === rtt / 2, String(syncErrorMsFrom(p)));
}

// ---------- clockOffsetMs: the SIGN is the whole contract ----------

{
  // The phone's clock reads 500 ms ahead of the server's. Positive means PHONE AHEAD; a consumer
  // converts to server time with `session_start_utc_ms - clock_offset_ms`.
  const serverUtcMs = 1_756_500_000_000;
  const tSendMs = serverUtcMs + 500 - 10;   // request left 10 ms before the server stamped
  const tRecvMs = serverUtcMs + 500 + 10;   // reply landed 10 ms after
  check("clockOffsetMs is +500 when the phone is 500 ms AHEAD",
        clockOffsetMs({ tSendMs, tRecvMs, serverUtcMs }) === 500,
        String(clockOffsetMs({ tSendMs, tRecvMs, serverUtcMs })));
  check("clockOffsetMs is -500 when the phone is 500 ms BEHIND",
        clockOffsetMs({ tSendMs: tSendMs - 1000, tRecvMs: tRecvMs - 1000, serverUtcMs }) === -500);
}

// ---------- isPlausibleEpochMs: refuse to send what the server would silently discard ----------

{
  const now = 1_756_500_000_000;
  check("isPlausibleEpochMs accepts a real now", isPlausibleEpochMs(now, now) === true);
  check("isPlausibleEpochMs rejects 0", isPlausibleEpochMs(0, now) === false);
  check("isPlausibleEpochMs rejects a negative", isPlausibleEpochMs(-1, now) === false);
  // The realistic unit error: seconds instead of milliseconds lands in 1970.
  check("isPlausibleEpochMs rejects seconds-not-milliseconds",
        isPlausibleEpochMs(Math.floor(now / 1000), now) === false);
  // ...and the other one: microseconds instead of milliseconds lands tens of thousands of years out.
  check("isPlausibleEpochMs rejects microseconds-not-milliseconds",
        isPlausibleEpochMs(now * 1000, now) === false);
  check("isPlausibleEpochMs rejects NaN", isPlausibleEpochMs(NaN, now) === false);
  check("isPlausibleEpochMs rejects Infinity", isPlausibleEpochMs(Infinity, now) === false);
  check("isPlausibleEpochMs rejects a non-number", isPlausibleEpochMs("1756500000000", now) === false);
  check("isPlausibleEpochMs accepts a fractional start (rounding happens at send)",
        isPlausibleEpochMs(now + 0.4, now) === true);
  check("isPlausibleEpochMs allows a phone up to 2 days fast",
        isPlausibleEpochMs(now + 47 * 3600 * 1000, now) === true);
  check("isPlausibleEpochMs rejects a phone 3 days fast",
        isPlausibleEpochMs(now + 72 * 3600 * 1000, now) === false);
}

// ---------- AC-3: the string that goes on the wire carries no decimal point ----------

{
  // Asserted against the EXACT expression RecordScreen uses, not a paraphrase of it.
  const startMs = 1_756_500_000_123.4;
  const wire = String(Math.round(startMs));
  check("session_start_utc_ms string is an integer", wire === "1756500000123", wire);
  check("session_start_utc_ms string contains no '.'", !wire.includes("."), wire);
  // Without Math.round this is what would reach FastAPI — a 422 before the handler, losing the swim.
  check("...and String() alone would NOT be safe", String(startMs).includes("."), String(startMs));
}

// ---------- probe-burst tuning is sane relative to the retrieval it front-runs ----------

check("META_PROBE_COUNT is a small positive integer",
      Number.isInteger(META_PROBE_COUNT) && META_PROBE_COUNT > 1 && META_PROBE_COUNT <= 20,
      String(META_PROBE_COUNT));
check("the worst-case burst cannot exceed the budget by more than one probe",
      META_PROBE_COUNT * META_PROBE_TIMEOUT_MS >= META_PROBE_BUDGET_MS,
      `${META_PROBE_COUNT}×${META_PROBE_TIMEOUT_MS} vs ${META_PROBE_BUDGET_MS}`);
check("the budget is well under the Phase 74 stall window (8000 ms)", META_PROBE_BUDGET_MS < 8000,
      String(META_PROBE_BUDGET_MS));

// ---------- cross-repo guard (AC-5): the phone's window must equal the server's ----------

{
  const apiSrc = fs.readFileSync(path.join(repo, "api.py"), "utf8");
  // The RHS captured by these regexes is only digits, spaces and `*`, so reducing the product is
  // safe — same approach as the MAX_VIDEO_BYTES guard in scratch/upload_retry_check.mjs.
  const reduce = (rhs) => rhs.trim().split("*").reduce((a, b) => a * Number(b.trim()), 1);
  const mFloor = apiSrc.match(/^_EPOCH_MS_FLOOR\s*=\s*([\d\s*]+)/m);
  const mSlack = apiSrc.match(/^_EPOCH_MS_FUTURE_SLACK_MS\s*=\s*([\d\s*]+)/m);
  check("api.py declares _EPOCH_MS_FLOOR", !!mFloor, mFloor ? mFloor[1].trim() : "not found");
  check("api.py declares _EPOCH_MS_FUTURE_SLACK_MS", !!mSlack, mSlack ? mSlack[1].trim() : "not found");
  if (mFloor) {
    const apiFloor = reduce(mFloor[1]);
    check("mobile EPOCH_MS_FLOOR === api.py _EPOCH_MS_FLOOR", EPOCH_MS_FLOOR === apiFloor,
          `mobile=${EPOCH_MS_FLOOR} api=${apiFloor}`);
  }
  if (mSlack) {
    const apiSlack = reduce(mSlack[1]);
    check("mobile EPOCH_MS_FUTURE_SLACK_MS === api.py _EPOCH_MS_FUTURE_SLACK_MS",
          EPOCH_MS_FUTURE_SLACK_MS === apiSlack,
          `mobile=${EPOCH_MS_FUTURE_SLACK_MS} api=${apiSlack}`);
  }
}

// ---------- source-level guard on the screen ----------

{
  // A text assertion is honest here: it guards a configuration fact, not behaviour — and it is the
  // one line whose removal turns a clock bug into a lost swim.
  const screen = fs.readFileSync(path.join(mobile, "src", "screens", "RecordScreen.js"), "utf8");
  const m = screen.match(/parameters\.session_start_utc_ms\s*=\s*([^;\n]+)/);
  check("RecordScreen assigns parameters.session_start_utc_ms", !!m, m ? m[1].trim() : "not found");
  check("...through Math.round (Optional[int] on the server — a fraction 422s the whole upload)",
        !!m && m[1].includes("Math.round"), m ? m[1].trim() : "");
  check("...and guarded by isPlausibleEpochMs", /isPlausibleEpochMs\(sessionStartUtcMsRef\.current/.test(screen));
  check("RecordScreen sends sync_error_ms", /parameters\.sync_error_ms\s*=/.test(screen));
  check("RecordScreen sends clock_offset_ms", /parameters\.clock_offset_ms\s*=/.test(screen));
  // GET /time must be unauthenticated — that is the whole point of 86-01's endpoint.
  check("the /time probe sends no Authorization header",
        /fetch\(`\$\{API_BASE\}\/time`,\s*\{\s*signal:/.test(screen));
  // Phase 74 constants are untouched by this plan.
  check("MAX_RETRIEVAL_ATTEMPTS is still 2", /const MAX_RETRIEVAL_ATTEMPTS = 2;/.test(screen));
  check("RETRIEVAL_STALL_MS is still 8000", /const RETRIEVAL_STALL_MS = 8000;/.test(screen));
}

console.log(`\n${pass}/${pass + fail} session-clock checks passed${fail ? `  (${fail} FAILED)` : ""}`);
process.exit(fail ? 1 : 0);
