/* ── OASIS Community Viewer — Live Mode ── */

const state = {
  data: null,
  filters: { author: "all", action: "all", search: "" },
  // Watermarks for incremental polling
  watermarks: { post_id: 0, comment_id: 0, trace_rowid: 0 },
  // Live polling
  liveEnabled: true,
  pollTimer: null,
  pollInterval: 3000,
  lastUpdate: null,
  // Tracking new items for highlighting
  knownPostIds: new Set(),
  knownTraceIds: new Set(),
  newPostIds: new Set(),
  // Stats
  updateCount: 0,
  errorCount: 0,
};

/* ── Helpers ── */

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

function timeAgo(isoStr) {
  if (!isoStr) return "";
  try {
    const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  } catch { return ""; }
}

/* ── Render functions ── */

function renderMeta(meta) {
  const metaBox = document.getElementById("meta");
  const ts = meta.exported_at ? timeAgo(meta.exported_at) : "unknown";
  const mode = meta.is_live ? "Live" : "Static";
  const inc = meta.is_incremental ? " (incremental)" : " (full)";
  metaBox.innerHTML = `
    <div class="meta-row"><strong>Mode:</strong> ${mode}${inc}</div>
    <div class="meta-row"><strong>Updated:</strong> ${ts}</div>
    <div class="meta-row"><strong>Polls:</strong> ${state.updateCount}</div>
  `;
}

function renderSummary(stats) {
  const summary = document.getElementById("summary");
  summary.innerHTML = "";
  const items = [
    ["Agents", stats.users, "user-icon"],
    ["Posts", stats.posts, "post-icon"],
    ["Comments", stats.comments, "comment-icon"],
    ["Likes", stats.likes, "like-icon"],
    ["Follows", stats.follows, "follow-icon"],
    ["Trace", stats.trace, "trace-icon"],
  ];
  for (const [label, value, icon] of items) {
    const card = el("div", "card");
    const title = el("h3", null, label);
    const val = el("div", "value", String(value));
    card.appendChild(title);
    card.appendChild(val);
    // Animate number change
    card.dataset.label = label;
    card.dataset.value = String(value);
    summary.appendChild(card);
  }
}

function buildSelectors(users, actions) {
  const authorSelect = document.getElementById("author-filter");
  const currentAuthor = state.filters.author;
  authorSelect.innerHTML = "";
  authorSelect.appendChild(new Option("All agents", "all"));
  users.forEach((u) => {
    authorSelect.appendChild(new Option(formatUser(u), String(u.user_id)));
  });
  authorSelect.value = currentAuthor;

  const actionSelect = document.getElementById("action-filter");
  const currentAction = state.filters.action;
  actionSelect.innerHTML = "";
  actionSelect.appendChild(new Option("All actions", "all"));
  actions.forEach((a) => actionSelect.appendChild(new Option(a, a)));
  actionSelect.value = currentAction;
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
  const autoScroll = document.getElementById("auto-scroll")?.checked;

  const filtered = posts
    .filter((p) => (authorFilter === "all" ? true : String(p.user_id) === authorFilter))
    .filter((p) => postMatchesSearch(p, search));

  // Show newest first for live feel
  const sorted = [...filtered].reverse();

  for (const post of sorted) {
    const isNew = state.newPostIds.has(post.post_id);
    const card = el("div", "post" + (isNew ? " post-new" : ""));
    card.dataset.postId = post.post_id;

    const header = el("div", "post-header");
    const userChip = el("span", "user-chip", formatUser(post.user));
    header.appendChild(userChip);
    const postId = el("span", "post-id", `#${post.post_id}`);
    header.appendChild(postId);
    if (isNew) {
      header.appendChild(el("span", "new-tag", "NEW"));
    }
    card.appendChild(header);

    card.appendChild(el("div", "post-content", post.content));

    const meta = el("div", "post-meta");
    meta.appendChild(el("span", null, `👍 ${post.num_likes || 0}`));
    meta.appendChild(el("span", null, `💬 ${(post.comments || []).length}`));
    meta.appendChild(el("span", null, `🔄 ${post.num_shares || 0}`));
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
  }

  // Clear new-post highlight after 6s
  if (state.newPostIds.size > 0) {
    setTimeout(() => {
      document.querySelectorAll(".post-new").forEach((el) => el.classList.remove("post-new"));
      state.newPostIds.clear();
    }, 6000);
  }

  // Badge
  const badge = document.getElementById("new-posts-badge");
  if (state.newPostIds.size > 0) {
    badge.textContent = `${state.newPostIds.size} new`;
    badge.style.display = "inline";
    setTimeout(() => { badge.style.display = "none"; }, 5000);
  }

  // Auto-scroll to top (newest)
  if (autoScroll && state.newPostIds.size > 0) {
    postsEl.scrollTop = 0;
  }
}

function renderTrace() {
  const traceEl = document.getElementById("trace");
  traceEl.innerHTML = "";
  const actionFilter = state.filters.action;

  const users = state.data.users || [];
  const userMap = new Map(users.map((u) => [u.user_id, u]));

  const actionColors = {
    create_post: "var(--accent-3)",
    create_comment: "var(--accent-2)",
    like_post: "var(--accent)",
    like_comment: "var(--accent)",
    dislike_post: "#ff6b6b",
    repost: "#c084fc",
    follow: "#34d399",
    unfollow: "#fb923c",
    refresh: "var(--muted)",
    sign_up: "#60a5fa",
  };

  state.data.trace
    .filter((t) => (actionFilter === "all" ? true : t.action === actionFilter))
    .slice(0, 200)
    .forEach((t) => {
      const item = el("div", "trace-item");
      const user = userMap.get(t.user_id);
      const color = actionColors[t.action] || "var(--accent-2)";
      item.innerHTML = `<span style="color:${color}">${t.action}</span> · ${formatUser(user)} · <span class="trace-time">${t.created_at}</span>`;
      traceEl.appendChild(item);
    });
}

function renderTopPosts() {
  const root = document.getElementById("top-posts");
  root.innerHTML = "";
  (state.data.top_posts || []).forEach((post) => {
    const item = el("div", "mini-item");
    const commentCount = (post.comments || []).length;
    const snippet = (post.content || "").substring(0, 40);
    item.innerHTML = `<strong>#${post.post_id}</strong> · ${commentCount} comments<br><span class="snippet">${snippet}...</span>`;
    root.appendChild(item);
  });
}

function renderAgentStats() {
  const root = document.getElementById("agent-stats");
  root.innerHTML = "";
  const users = state.data.users || [];
  const perUser = state.data.per_user_actions || {};
  const commentsByUser = state.data.comments_by_user || {};

  users.forEach((u) => {
    const item = el("div", "mini-item agent-stat-item");
    const actions = perUser[u.user_id] || {};
    const posts = actions["create_post"] || 0;
    const comments = commentsByUser[u.user_id] || 0;
    const likes = actions["like_post"] || 0;
    item.innerHTML = `<strong>${formatUser(u)}</strong><br>` +
      `<span class="stat-detail">📝${posts} 💬${comments} 👍${likes}</span>`;
    root.appendChild(item);
  });
}

/* ── Data fetching with incremental support ── */

async function fetchData(full = false) {
  try {
    let url;
    if (full || state.watermarks.post_id === 0) {
      url = "/api/data?full=1";
    } else {
      url = `/api/data?since_post_id=${state.watermarks.post_id}` +
            `&since_comment_id=${state.watermarks.comment_id}` +
            `&since_trace_rowid=${state.watermarks.trace_rowid}`;
    }

    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    if (data.error) {
      setLiveStatus("error", data.message || "DB not found");
      return;
    }

    state.updateCount++;

    if (data.meta?.is_incremental && state.data) {
      // Merge incremental data
      mergeIncremental(data);
    } else {
      // Full replace
      const oldPostIds = state.data
        ? new Set((state.data.posts || []).map(p => p.post_id))
        : new Set();

      state.data = data;

      // Mark new posts
      state.newPostIds.clear();
      if (oldPostIds.size > 0) {
        for (const p of data.posts || []) {
          if (!oldPostIds.has(p.post_id)) {
            state.newPostIds.add(p.post_id);
          }
        }
      }

      // Track known IDs
      for (const p of data.posts || []) state.knownPostIds.add(p.post_id);
    }

    // Update watermarks
    if (data.watermarks) {
      state.watermarks = { ...data.watermarks };
    }

    state.lastUpdate = new Date();
    renderAll();
    setLiveStatus("connected", `Updated ${timeAgo(state.lastUpdate.toISOString())}`);
    state.errorCount = 0;

  } catch (err) {
    state.errorCount++;
    console.error("Fetch error:", err);

    // Try fallback: static data.json
    if (state.errorCount === 1 && !state.data) {
      try {
        const resp = await fetch("data.json");
        state.data = await resp.json();
        renderAll();
        setLiveStatus("static", "Loaded static data.json (server not running)");
        return;
      } catch { /* ignore */ }
    }

    if (state.errorCount > 3) {
      setLiveStatus("error", `Connection lost (${state.errorCount} failures)`);
    } else {
      setLiveStatus("error", `Retry... (${err.message})`);
    }
  }
}

function mergeIncremental(newData) {
  if (!state.data) return;

  // Merge new posts
  const existingPostIds = new Set(state.data.posts.map(p => p.post_id));
  state.newPostIds.clear();
  for (const p of newData.posts || []) {
    if (!existingPostIds.has(p.post_id)) {
      state.data.posts.push(p);
      state.newPostIds.add(p.post_id);
      state.knownPostIds.add(p.post_id);
    }
  }

  // Update stats, action_summary, trace etc. from server
  state.data.stats = newData.stats;
  state.data.action_summary = newData.action_summary;
  state.data.trace = newData.trace;
  state.data.users = newData.users;
  state.data.comments_by_user = newData.comments_by_user;
  state.data.likes_by_user = newData.likes_by_user;
  state.data.per_user_actions = newData.per_user_actions;
  state.data.top_posts = newData.top_posts;
  state.data.meta = newData.meta;

  // Refresh comments on existing posts (comments may have been added)
  const userMap = new Map((newData.users || []).map(u => [u.user_id, u]));
  // Re-fetch full posts for updated comment counts is handled by top_posts
}

function renderAll() {
  if (!state.data) return;
  renderMeta(state.data.meta || { exported_at: "unknown" });
  renderSummary(state.data.stats || {});
  buildSelectors(state.data.users || [], Object.keys(state.data.action_summary || {}));
  renderPosts();
  renderTrace();
  renderTopPosts();
  renderAgentStats();
}

/* ── Live status indicator ── */

function setLiveStatus(status, text) {
  const indicator = document.getElementById("live-indicator");
  const textEl = document.getElementById("live-text");
  indicator.className = "live-indicator live-" + status;
  textEl.textContent = text;

  const footer = document.getElementById("footer-status");
  if (status === "connected") {
    footer.textContent = `Live · ${state.updateCount} updates · ${(state.data?.stats?.posts || 0)} posts`;
  } else if (status === "static") {
    footer.textContent = "Static mode · data.json";
  } else {
    footer.textContent = text;
  }
}

/* ── Polling control ── */

function startPolling() {
  stopPolling();
  state.liveEnabled = true;
  state.pollTimer = setInterval(() => fetchData(false), state.pollInterval);
  document.getElementById("btn-live-icon").textContent = "⏸";
  setLiveStatus("connected", "Live polling...");
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  state.liveEnabled = false;
  document.getElementById("btn-live-icon").textContent = "▶";
  setLiveStatus("paused", "Paused");
}

function togglePolling() {
  if (state.liveEnabled) {
    stopPolling();
  } else {
    startPolling();
  }
}

/* ── Init ── */

async function init() {
  // Bind event listeners
  document.getElementById("btn-toggle-live").addEventListener("click", togglePolling);
  document.getElementById("btn-refresh").addEventListener("click", () => fetchData(true));
  document.getElementById("poll-interval").addEventListener("change", (e) => {
    state.pollInterval = parseInt(e.target.value, 10);
    if (state.liveEnabled) startPolling(); // restart with new interval
  });

  document.getElementById("author-filter").addEventListener("change", (e) => {
    state.filters.author = e.target.value;
    renderPosts();
    renderTrace();
  });
  document.getElementById("action-filter").addEventListener("change", (e) => {
    state.filters.action = e.target.value;
    renderTrace();
  });
  document.getElementById("search").addEventListener("input", (e) => {
    state.filters.search = e.target.value.toLowerCase();
    renderPosts();
  });

  // Initial full fetch
  setLiveStatus("connecting", "Connecting...");
  await fetchData(true);

  // Start live polling
  startPolling();
}

init();
