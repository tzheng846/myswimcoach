// Phase 61-02 D4 — the one thing that survives the Data Quality card.
//
// Mirrors swimnetics-mobile/src/lib/dropoutWarning.js so the two clients cannot disagree about
// the same session. Keep the threshold and the predicate identical in both.
//
// Dropout is the only stat on that card that never touched the segmenter: api.py counts
// `magnet_ok == 0` rows straight out of the raw CSV — samples where the AS5600 failed its I2C
// read (magnet misaligned, wheel wobbling, connector loose). It is hardware truth, and the
// visible product of a real firmware fix: angle == 4095 used to pass through as valid data until
// readAngle() began error-checking and flagging magnet_ok = 0.
//
// The card's other three stats (total_cycles_raw / outlier_cycle_count / implausible_cycle_count)
// are segmentation-derived, and Phase 59 replaced the segmenter for every stroke. The implausible
// rails are also hardcoded 0.5–4.0 s under a comment reading "physically reasonable BREASTSTROKE
// range" — written in Phase 10, never revisited.
//
// ⚠⚠ DO NOT gate any display on `warnings.length > 0`. TWO of the warnings api.py emits fire on
// essentially every session and carry zero information:
//   - the kick warning is appended UNCONDITIONALLY (api.py:181)
//   - the segmentation warning fires whenever `segmentation_reliable` is false (api.py:193),
//     and that flag is hardcoded false for every auto-segmented session
// A `warnings.length` predicate therefore flags everything. Phase 58-05 caught this trap on the
// web, Phase 60-01 documented it on mobile, and it is why this helper looks at exactly one number.

export const DROPOUT_WARN_PCT = 5;

/**
 * @param {{magnet_dropout_pct?: number}|null|undefined} dataQuality
 * @returns {string|null} the warning to display, or null when there is nothing worth saying
 */
export function dropoutWarning(dataQuality) {
  const pct = dataQuality?.magnet_dropout_pct;
  if (typeof pct !== "number" || Number.isNaN(pct) || pct <= DROPOUT_WARN_PCT) {
    return null;
  }
  return `Encoder signal lost for ${pct.toFixed(
    1
  )}% of samples — this recording may be unreliable`;
}
