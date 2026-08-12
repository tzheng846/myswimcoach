// Deterministic, human-tellable session labels (61-04 D8).
//
// The trigger: on Compare, sessions recorded on the same day were byte-identical in the dropdown.
// The old label was `name — date`, and `name` is usually null, so three sessions from one morning
// all read "Aug 7, 2026" and there was no way to pick the right one.
//
// ⚠ DERIVED AT RENDER TIME. NEVER WRITTEN TO sessions.name. That column is coach-editable and
// PATCHable (`PATCH /sessions/{id}`), so generating into it would silently overwrite names the
// coach typed. It also means these labels work retroactively on every stored session with no
// migration and no backfill.
//
// Stability matters as much as distinctness: the same id must produce the same pair on every
// render, every reload, and every machine. Hence a pure hash of the id — no randomness, no
// counters, no dependence on list position or fetch order.

const ADJECTIVES = [
  "Amber", "Azure", "Bright", "Bronze", "Calm", "Cobalt", "Copper", "Coral",
  "Crimson", "Dusky", "Eager", "Ember", "Fleet", "Frosted", "Gilded", "Golden",
  "Hazel", "Indigo", "Ivory", "Jade", "Keen", "Lucid", "Mellow", "Nimble",
  "Olive", "Opal", "Pearl", "Quick", "Russet", "Sable", "Scarlet", "Silver",
  "Slate", "Smooth", "Steady", "Swift", "Teal", "Umber", "Velvet", "Wild",
];

const NOUNS = [
  "Otter", "Heron", "Marlin", "Dolphin", "Falcon", "Gannet", "Kingfisher", "Manta",
  "Narwhal", "Orca", "Osprey", "Pelican", "Petrel", "Puffin", "Ray", "Sailfish",
  "Seal", "Shark", "Skua", "Swift", "Tarpon", "Tern", "Trout", "Tuna",
  "Turtle", "Walrus", "Whale", "Wrasse", "Albatross", "Barracuda", "Cormorant", "Dorado",
];

// FNV-1a. Chosen for being short, dependency-free and well-distributed on short strings —
// UUIDs share long prefixes, so a weak hash (e.g. summing char codes) would collide visibly.
function hash32(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Stable two-word mnemonic for a session id. Same id → same words, always. */
export function mnemonic(id) {
  if (!id) return "Unnamed";
  const h = hash32(String(id));
  // Independent halves, so the two words vary independently rather than in lockstep.
  const a = ADJECTIVES[h % ADJECTIVES.length];
  const n = NOUNS[Math.floor(h / ADJECTIVES.length) % NOUNS.length];
  return `${a} ${n}`;
}

function timeOfDay(createdAt) {
  if (!createdAt) return null;
  const d = new Date(createdAt);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

/**
 * Full dropdown label.
 *
 * ⚠ The TIME is the load-bearing part for same-day sessions — the date alone is exactly what
 * failed. The mnemonic makes a session sayable out loud; the time makes it findable.
 * A coach-typed name always wins the front position; the mnemonic still trails it so the two
 * naming schemes never compete for the same slot.
 */
export function sessionLabel(session) {
  if (!session) return "";
  const words = mnemonic(session.id);
  const t = timeOfDay(session.created_at);
  const typed = session.name?.trim();
  const head = typed ? `${typed} · ${words}` : words;
  return t ? `${head} · ${t}` : head;
}

/** Date line, kept separate so callers can show it without duplicating it into the label. */
export function sessionDate(session) {
  if (!session?.created_at) return "";
  return new Date(session.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
