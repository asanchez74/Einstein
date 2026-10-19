"use strict";

// Interface Einstein (ADR-0011) : aucun contenu n'est inséré comme HTML.

const $ = (id) => document.getElementById(id);

class AuthRequired extends Error {}

async function api(path, options = {}) {
  const init = { credentials: "same-origin", ...options };
  if (init.body !== undefined) {
    init.method = init.method || "POST";
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(init.body);
  }
  const response = await fetch(path, init);
  if (response.status === 401 && !path.endsWith("/auth/connexion")) {
    showLogin();
    throw new AuthRequired();
  }
  let data = null;
  if (response.status !== 204) {
    try { data = await response.json(); } catch { data = null; }
  }
  if (!response.ok) {
    const detail = data && typeof data.detail === "string" ? data.detail : `Erreur ${response.status}`;
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return data;
}

function show(id, visible) { $(id).hidden = !visible; }

function showLogin() {
  show("app", false);
  show("logout", false);
  show("login", true);
  $("password").value = "";
  $("password").focus();
}

function showApp(canLogout) {
  show("login", false);
  show("app", true);
  show("logout", canLogout);
  selectTab("search");
}

function selectTab(name) {
  for (const tab of document.querySelectorAll("[role=tab]")) {
    const active = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(active));
    show(`tab-${tab.dataset.tab}`, active);
  }
  if (name === "search") $("query").focus();
  if (name === "question") $("question").focus();
  if (name === "inventory") loadInventory();
}

async function busy(button, task) {
  button.disabled = true;
  try { await task(); } finally { button.disabled = false; }
}

// Connexion

$("login-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const button = event.submitter;
  busy(button, async () => {
    show("login-error", false);
    try {
      await api("/api/v1/auth/connexion", { body: { password: $("password").value } });
      showApp(true);
    } catch (error) {
      $("login-error").textContent = error.message;
      show("login-error", true);
      $("password").select();
    }
  });
});

$("logout").addEventListener("click", async () => {
  try { await api("/api/v1/auth/deconnexion", { body: {} }); } catch { /* session déjà close */ }
  showLogin();
});

for (const tab of document.querySelectorAll("[role=tab]")) {
  tab.addEventListener("click", () => selectTab(tab.dataset.tab));
}

// Recherche documentaire

const normalize = (text) => text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

function highlighted(text, terms) {
  const fragment = document.createDocumentFragment();
  let last = 0;
  for (const match of text.matchAll(/[\p{L}\p{N}_]+/gu)) {
    if (!terms.has(normalize(match[0]))) continue;
    fragment.append(text.slice(last, match.index));
    const mark = document.createElement("mark");
    mark.textContent = match[0];
    fragment.append(mark);
    last = match.index + match[0].length;
  }
  fragment.append(text.slice(last));
  return fragment;
}

function resultItem(hit, terms) {
  const item = document.createElement("li");
  const head = document.createElement("div");
  head.className = "head";
  const title = document.createElement("span");
  title.className = "title";
  title.textContent = hit.source;
  head.append(title);
  if (hit.page !== null) {
    const page = document.createElement("span");
    page.className = "muted";
    page.textContent = `page ${hit.page}`;
    head.append(page);
  }
  if (hit.ocr) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.title = "Texte issu de la reconnaissance de caractères : erreurs possibles";
    badge.textContent = "OCR";
    head.append(badge);
  }
  const link = document.createElement("a");
  link.href = `/api/v1/documents/fichier?source=${encodeURIComponent(hit.source)}`;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = "Ouvrir";
  head.append(link);
  const excerpt = document.createElement("p");
  excerpt.className = "excerpt";
  excerpt.append(highlighted(hit.excerpt, terms));
  item.append(head, excerpt);
  return item;
}

$("search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const query = $("query").value.trim();
  if (!query) return;
  busy(event.submitter, async () => {
    $("search-results").replaceChildren();
    $("search-status").textContent = "Recherche…";
    try {
      const result = await api("/api/v1/documents/recherche", { body: { query, limit: 20 } });
      const terms = new Set((normalize(query).match(/[\p{L}\p{N}_]+/gu) || []));
      $("search-results").replaceChildren(...result.results.map((hit) => resultItem(hit, terms)));
      const found = result.results.length;
      const indexed = new Date(result.indexed_at).toLocaleString("fr-CH");
      $("search-status").textContent =
        `${found} document${found > 1 ? "s" : ""} trouvé${found > 1 ? "s" : ""} · ` +
        `${result.indexed_files} indexés, ${result.skipped_files} écartés · index du ${indexed}`;
    } catch (error) {
      if (!(error instanceof AuthRequired)) $("search-status").textContent = error.message;
    }
  });
});

// Questions sur l'inventaire

function answerText(text) {
  // Seul le gras Markdown (**…**) est rendu ; le reste reste du texte brut.
  const fragment = document.createDocumentFragment();
  text.split(/\*\*(.+?)\*\*/g).forEach((part, index) => {
    if (index % 2) {
      const strong = document.createElement("strong");
      strong.textContent = part;
      fragment.append(strong);
    } else {
      fragment.append(part);
    }
  });
  return fragment;
}

$("question-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) return;
  busy(event.submitter, async () => {
    show("answer", false);
    $("question-status").textContent = "Question transmise à l'IA…";
    try {
      const answer = await api("/api/v1/maison/questions", { body: { question } });
      const meta = document.createElement("span");
      meta.className = "meta muted";
      meta.textContent = `${answer.provider} · ${answer.model}`;
      $("answer").replaceChildren(answerText(answer.answer), meta);
      show("answer", true);
      $("question-status").textContent = "";
    } catch (error) {
      if (!(error instanceof AuthRequired)) $("question-status").textContent = error.message;
    }
  });
});

// Inventaire

async function loadInventory() {
  $("inventory-status").textContent = "Chargement…";
  try {
    const items = await api("/api/v1/maison/equipements");
    $("inventory").replaceChildren(...items.map((item) => {
      const li = document.createElement("li");
      const name = document.createElement("div");
      name.className = "name";
      name.textContent = item.name;
      const details = document.createElement("div");
      const address = document.createElement("code");
      address.textContent = item.address;
      details.append(address, ` · ${item.category} · ${item.role}`);
      li.append(name, details);
      return li;
    }));
    $("inventory-status").textContent = `${items.length} équipement${items.length > 1 ? "s" : ""}`;
  } catch (error) {
    if (!(error instanceof AuthRequired)) $("inventory-status").textContent = error.message;
  }
}

// Démarrage : session existante, connexion requise, ou authentification désactivée.

(async () => {
  try {
    const session = await api("/api/v1/auth/session");
    showApp(session.required);
  } catch {
    /* showLogin a déjà été appelé sur 401 */
  }
})();
