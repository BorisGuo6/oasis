const state = {
  data: null,
  filters: {
    author: "all",
    action: "all",
    search: "",
  },
};

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatUser(user) {
  if (!user) return "Unknown";
  if (user.name && user.user_name) return `${user.name} (@${user.user_name})`;
  if (user.name) return user.name;
  if (user.user_name) return `@${user.user_name}`;
  return "Unknown";
}

function renderMeta(meta) {
  const metaBox = document.getElementById("meta");
  metaBox.textContent = `Exported: ${meta.exported_at}`;
}

function renderSummary(stats) {
  const summary = document.getElementById("summary");
  summary.innerHTML = "";
  const items = [
    ["Agents", stats.users],
    ["Posts", stats.posts],
    ["Comments", stats.comments],
    ["Likes", stats.likes],
    ["Follows", stats.follows],
    ["Trace", stats.trace],
  ];
  for (const [label, value] of items) {
    const card = el("div", "card");
    const title = el("h3", null, label);
    const val = el("div", "value", value);
    card.appendChild(title);
    card.appendChild(val);
    summary.appendChild(card);
  }
}

function buildSelectors(users, actions) {
  const authorSelect = document.getElementById("author-filter");
  authorSelect.innerHTML = "";
  authorSelect.appendChild(new Option("All agents", "all"));
  users.forEach((u) => {
    authorSelect.appendChild(new Option(formatUser(u), String(u.user_id)));
  });

  const actionSelect = document.getElementById("action-filter");
  actionSelect.innerHTML = "";
  actionSelect.appendChild(new Option("All actions", "all"));
  actions.forEach((a) => actionSelect.appendChild(new Option(a, a)));

  authorSelect.addEventListener("change", (e) => {
    state.filters.author = e.target.value;
    renderPosts();
    renderTrace();
  });
  actionSelect.addEventListener("change", (e) => {
    state.filters.action = e.target.value;
    renderTrace();
  });

  document.getElementById("search").addEventListener("input", (e) => {
    state.filters.search = e.target.value.toLowerCase();
    renderPosts();
  });
}

function postMatchesSearch(post, query) {
  if (!query) return true;
  const haystack = [post.content, ...(post.comments || []).map((c) => c.content || "")]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query);
}

function renderPosts() {
  const postsEl = document.getElementById("posts");
  postsEl.innerHTML = "";
  const posts = state.data.posts || [];
  const authorFilter = state.filters.author;
  const search = state.filters.search;

  posts
    .filter((p) => (authorFilter === "all" ? true : String(p.user_id) === authorFilter))
    .filter((p) => postMatchesSearch(p, search))
    .forEach((post) => {
      const card = el("div", "post");

      const header = el("div", "post-header");
      header.appendChild(el("div", null, formatUser(post.user)));
      header.appendChild(el("div", null, `Post #${post.post_id}`));
      card.appendChild(header);

      card.appendChild(el("div", "post-content", post.content));

      const meta = el("div", "post-meta");
      meta.appendChild(el("div", null, `Likes ${post.num_likes}`));
      meta.appendChild(el("div", null, `Comments ${(post.comments || []).length}`));
      meta.appendChild(el("div", null, `Shares ${post.num_shares}`));
      card.appendChild(meta);

      (post.comments || []).forEach((c) => {
        const cEl = el("div", "comment");
        const author = formatUser(c.user);
        const label = el("strong", null, author);
        cEl.appendChild(label);
        cEl.appendChild(document.createTextNode(` — ${c.content}`));
        card.appendChild(cEl);
      });

      postsEl.appendChild(card);
    });
}

function renderTrace() {
  const traceEl = document.getElementById("trace");
  traceEl.innerHTML = "";
  const actionFilter = state.filters.action;

  const users = state.data.users || [];
  const userMap = new Map(users.map((u) => [u.user_id, u]));

  state.data.trace
    .filter((t) => (actionFilter === "all" ? true : t.action === actionFilter))
    .slice(0, 200)
    .forEach((t) => {
      const item = el("div", "trace-item");
      const user = userMap.get(t.user_id);
      item.innerHTML = `<span>${t.action}</span> · ${formatUser(user)} · ${t.created_at}`;
      traceEl.appendChild(item);
    });
}

function renderTopPosts() {
  const root = document.getElementById("top-posts");
  root.innerHTML = "";
  (state.data.top_posts || []).forEach((post) => {
    const item = el("div", "mini-item");
    item.textContent = `#${post.post_id} · ${(post.comments || []).length} comments`;
    root.appendChild(item);
  });
}

function renderAgentStats() {
  const root = document.getElementById("agent-stats");
  root.innerHTML = "";
  const users = state.data.users || [];
  const commentsByUser = state.data.comments_by_user || {};
  users.forEach((u) => {
    const item = el("div", "mini-item");
    const count = commentsByUser[u.user_id] || 0;
    item.textContent = `${formatUser(u)} · ${count} comments`;
    root.appendChild(item);
  });
}

async function init() {
  try {
    const resp = await fetch("data.json");
    state.data = await resp.json();
    renderMeta(state.data.meta || { exported_at: "unknown" });
    renderSummary(state.data.stats || {});
    buildSelectors(state.data.users || [], Object.keys(state.data.action_summary || {}));
    renderPosts();
    renderTrace();
    renderTopPosts();
    renderAgentStats();
  } catch (err) {
    const meta = document.getElementById("meta");
    meta.textContent = "Failed to load data.json. Run export.py and serve over HTTP.";
    console.error(err);
  }
}

init();
