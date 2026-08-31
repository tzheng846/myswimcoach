// Phase 84-05 check for the mobile app's upload-failure classifier.
//
// The mobile tree has no test runner (84-03 G28), so `src/lib/uploadRetry.js` was written with ZERO
// imports specifically to be checkable from here. It decides whether a failed video upload is worth
// retrying — the fix for Phase 84 item 2, where every non-2xx became "Server error (413)", burned
// two more attempts on a deterministic rejection, and showed the coach a constant string.
//
// Also guards the cross-repo constant: MAX_VIDEO_BYTES exists in THREE places (api.py — the
// authoritative one, web/components/portal/VideoPane.js, and the mobile module). Nothing imports
// across the repo boundary, so this parses api.py and fails if the mobile copy has drifted.
//
// Run: node scratch/upload_retry_check.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..");
const modulePath = path.resolve(repo, "..", "swimnetics-mobile", "src", "lib", "uploadRetry.js");

// swimnetics-mobile/package.json has no `"type": "module"`, so Node would treat this .js as CJS and
// choke on its `export` statements. Loading the source through a data: URL imports it AS an ES
// module without touching the mobile tree — safe precisely because the module has no imports of
// its own to resolve.
const src = fs.readFileSync(modulePath, "utf8");
const mod = await import(`data:text/javascript,${encodeURIComponent(src)}`);
const { MAX_VIDEO_BYTES, classifyUploadFailure, videoTooLargeMessage, videoMissingMessage } = mod;

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

// ---------- permanent: retrying cannot change the outcome ----------

for (const status of [413, 401, 403, 404, 422]) {
  const r = classifyUploadFailure({ status });
  check(`${status} is permanent`, r.permanent === true, `permanent=${r.permanent}`);
  check(`${status} has a non-empty message`, typeof r.message === "string" && r.message.length > 10);
  check(`${status} message does not show the raw status code`, !r.message.includes(String(status)),
        JSON.stringify(r.message));
}

// ---------- transient: worth another attempt ----------

for (const status of [429, 500, 502, 503]) {
  const r = classifyUploadFailure({ status });
  check(`${status} is transient`, r.permanent === false, `permanent=${r.permanent}`);
  check(`${status} has a non-empty message`, typeof r.message === "string" && r.message.length > 10);
}

// A network/offline failure arrives with NO status at all — this is the case that must stay
// retryable, or a flaky pool wifi would silently discard the clip.
for (const message of ["Network request failed", "The request timed out", "connection lost", ""]) {
  const r = classifyUploadFailure({ message });
  check(`no-status error is transient  (${JSON.stringify(message)})`, r.permanent === false,
        `permanent=${r.permanent}`);
}
check("no-status offline error reads as offline",
      /offline/i.test(classifyUploadFailure({ message: "Network request failed" }).message),
      JSON.stringify(classifyUploadFailure({ message: "Network request failed" }).message));

// Called with nothing at all (a defensive path) must not throw.
{
  let threw = false;
  try { classifyUploadFailure(); } catch { threw = true; }
  check("classifyUploadFailure() with no argument does not throw", !threw);
}

// ---------- the size message names the real number, not just the cap ----------

{
  const msg = videoTooLargeMessage(78 * 1024 * 1024);
  check("videoTooLargeMessage names the actual size", msg.includes("78"), JSON.stringify(msg));
  check("videoTooLargeMessage names the 50 MB limit", msg.includes("50"));
  check("videoTooLargeMessage rounds to whole MB", !/\d+\.\d/.test(msg));
  const odd = videoTooLargeMessage(53.7 * 1024 * 1024);
  check("videoTooLargeMessage rounds 53.7 MB to 54", odd.includes("54"), JSON.stringify(odd));
  check("videoMissingMessage is non-empty", (videoMissingMessage() || "").length > 10);
}

// ---------- cross-repo constant: the mobile copy must not drift from api.py ----------

{
  const apiSrc = fs.readFileSync(path.join(repo, "api.py"), "utf8");
  const m = apiSrc.match(/^MAX_VIDEO_BYTES\s*=\s*([\d\s*]+)/m);
  check("api.py declares MAX_VIDEO_BYTES", !!m, m ? m[1].trim() : "not found");
  if (m) {
    // The captured RHS is only digits, spaces and `*` — the regex guarantees it.
    const apiValue = m[1].trim().split("*").reduce((a, b) => a * Number(b.trim()), 1);
    check("mobile MAX_VIDEO_BYTES === api.py MAX_VIDEO_BYTES", MAX_VIDEO_BYTES === apiValue,
          `mobile=${MAX_VIDEO_BYTES} api=${apiValue}`);
  }
}

console.log(`\n${pass}/${pass + fail} upload-retry checks passed${fail ? `  (${fail} FAILED)` : ""}`);
process.exit(fail ? 1 : 0);
