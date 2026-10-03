// Persistence: the viewer's private db subtree (data/users/<id>/…) when the artifact runtime grants it,
// otherwise browser storage. Writes are debounced and serialised per document.

const LS_PREFIX = "analyst-lab:v1:";
const DEBOUNCE_MS = 700;

function lsGet(key) {
  try {
    const raw = window.localStorage.getItem(LS_PREFIX + key);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}
function lsSet(key, value) {
  try {
    window.localStorage.setItem(LS_PREFIX + key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

async function useCap(name) {
  try {
    if (!window.claude || typeof window.claude.use !== "function") return null;
    return await window.claude.use(name);
  } catch {
    return null;
  }
}

export function createStore(onStatus) {
  let db = null;
  let uid = null;
  let mode = "local"; // "account" | "local" | "none"
  const timers = {};
  const pending = {};
  const inflight = {};
  const retried = {};

  const status = (s) => onStatus && onStatus({ mode, ...s });

  async function init() {
    const [dbCap, userCap] = await Promise.all([useCap("db"), useCap("user")]);
    if (dbCap && userCap) {
      try {
        const id = await userCap.id();
        if (id) {
          db = dbCap;
          uid = id;
          mode = "account";
        }
      } catch {
        /* stay local */
      }
    }
    if (mode !== "account") {
      mode = lsSet("probe", 1) ? "local" : "none";
    }
    status({ state: "idle" });
    return mode;
  }

  const ref = (key) => db.doc(`data/users/${uid}/${key}`);

  async function load(key) {
    if (mode === "account") {
      try {
        const snap = await ref(key).get();
        if (snap.exists) return JSON.parse(JSON.stringify(snap.data()));
        // first visit with an account: migrate anything kept in this browser
        return lsGet(key);
      } catch {
        return lsGet(key);
      }
    }
    return lsGet(key);
  }

  async function flush(key) {
    if (inflight[key]) return; // the running write picks up the newest value when it ends
    const value = pending[key];
    if (value === undefined) return;
    delete pending[key];
    inflight[key] = true;
    status({ state: "saving" });
    lsSet(key, value); // always keep a local copy as a safety net
    let ok = true;
    if (mode === "account") {
      try {
        await ref(key).set(JSON.parse(JSON.stringify(value))); // plain JSON only (drops undefined, NaN → null)
        retried[key] = false;
      } catch (e) {
        ok = false;
        if (e && (e.code === "invalid_argument" || e.code === "not_granted" || e.code === "revoked")) {
          mode = "local"; // read-only viewer: keep working in this browser
        } else if (e && e.code === "unavailable" && !retried[key]) {
          retried[key] = true; // retry once after a short randomized delay
          pending[key] = pending[key] ?? value;
          setTimeout(() => flush(key), 1500 + Math.random() * 1000);
        }
      }
    }
    inflight[key] = false;
    status({ state: ok ? "saved" : "error", at: Date.now() });
    if (pending[key] !== undefined) flush(key);
  }

  function save(key, value) {
    pending[key] = value;
    clearTimeout(timers[key]);
    timers[key] = setTimeout(() => flush(key), DEBOUNCE_MS);
    status({ state: "dirty" });
  }

  async function remove(key) {
    try {
      window.localStorage.removeItem(LS_PREFIX + key);
    } catch {
      /* ignore */
    }
    if (mode === "account") {
      try {
        await ref(key).delete();
      } catch {
        /* ignore */
      }
    }
  }

  return { init, load, save, remove, getMode: () => mode };
}

// ------------------------------------------------------------------ downloads

let downloadsCap;
export async function getDownloads() {
  if (downloadsCap === undefined) downloadsCap = await useCap("downloads");
  return downloadsCap;
}

/** Offer a file to the viewer. Returns "saved" | "declined" | "unavailable" | "error". */
export async function offerDownload(filename, data) {
  const d = await getDownloads();
  if (!d) return "unavailable";
  try {
    await d.save({ filename, data });
    return "saved";
  } catch (e) {
    if (e && e.code === "declined") return "declined";
    if (e && ["unavailable", "not_granted", "capability_disabled", "capability_removed"].includes(e.code)) return "unavailable";
    return "error";
  }
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}
