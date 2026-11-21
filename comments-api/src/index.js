/*
 * databrew NOW guest comments — Cloudflare Worker + D1 + Turnstile.
 * No Github account, user login, or browser-exposed write credential.
 * All comments start pending; only admin-approved comments are public.
 */
const MAX_BODY = 3500;
const POST_KEY = /^(watch|stories|projects):[A-Za-z0-9_:.%-]{1,180}$/;

function cors(origin, env) {
  const allowed = String(env.ALLOWED_ORIGIN || "https://raspos.github.io");
  return origin === allowed ? {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  } : { Vary: "Origin" };
}

function reply(obj, status, origin, env, extra = {}) {
  return new Response(JSON.stringify(obj), {
    status, headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      ...cors(origin, env), ...extra,
    },
  });
}

function assertConfig(env) {
  if (!env.DB || !env.TURNSTILE_SECRET || !env.COMMENT_HASH_SALT || !env.ADMIN_TOKEN) {
    throw new Error("Worker bindings or secrets are not configured");
  }
}

async function hashIp(ip, secret) {
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const bytes = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(ip));
  return Array.from(new Uint8Array(bytes)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function captchaOkay(token, ip, env) {
  if (typeof token !== "string" || token.length < 10 || token.length > 4096) return false;
  const data = new FormData();
  data.set("secret", env.TURNSTILE_SECRET);
  data.set("response", token);
  if (ip) data.set("remoteip", ip);
  let result;
  try {
    const response = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST", body: data,
    });
    if (!response.ok) return false;
    result = await response.json();
  } catch {
    return false;
  }
  // Server-side validation is mandatory. Reject tokens issued on other hosts.
  return result.success === true &&
    result.hostname === (env.TURNSTILE_HOSTNAME || "raspos.github.io");
}

function validPostKey(key) {
  return typeof key === "string" && POST_KEY.test(key);
}

function trimText(v, max) {
  return typeof v === "string" ? v.trim().slice(0, max + 1) : "";
}

function validName(name) {
  // Only a display name; no email or real-name requirement.
  return name.length >= 2 && name.length <= 24 && !/[<>]/.test(name) && !/[\r\n]/.test(name);
}

function validMessage(text) {
  return text.length >= 2 && text.length <= 1000 && !/[\x00-\x08\x0B\x0C\x0E-\x1F]/.test(text);
}

async function listComments(url, env, origin) {
  const key = url.searchParams.get("post");
  if (!validPostKey(key)) return reply({ error: "게시물 주소가 올바르지 않습니다." }, 400, origin, env);
  const limit = Math.min(50, Math.max(1, Number(url.searchParams.get("limit")) || 30));
  const query = await env.DB.prepare(
    "SELECT id, nickname, content, created_at FROM comments WHERE post_key = ? AND status = 'approved' ORDER BY created_at DESC, id DESC LIMIT ?"
  ).bind(key, limit).all();
  const total = await env.DB.prepare(
    "SELECT count(*) AS n FROM comments WHERE post_key = ? AND status = 'approved'"
  ).bind(key).first();
  return reply({ comments: query.results || [], count: Number(total?.n || 0) }, 200, origin, env);
}

async function submitComment(request, env, origin) {
  if (origin !== (env.ALLOWED_ORIGIN || "https://raspos.github.io")) {
    return reply({ error: "허용되지 않은 사이트입니다." }, 403, origin, env);
  }
  const bytes = Number(request.headers.get("content-length") || "0");
  if (bytes > MAX_BODY) return reply({ error: "글이 너무 깁니다." }, 413, origin, env);
  const raw = await request.text();
  if (raw.length > MAX_BODY) return reply({ error: "글이 너무 깁니다." }, 413, origin, env);
  let body;
  try { body = JSON.parse(raw); } catch { return reply({ error: "요청 형식이 올바르지 않습니다." }, 400, origin, env); }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return reply({ error: "요청 형식이 올바르지 않습니다." }, 400, origin, env);
  }
  const key = body.post_key, name = trimText(body.nickname, 25), message = trimText(body.content, 1001);
  if (!validPostKey(key) || !validName(name) || !validMessage(message)) {
    return reply({ error: "닉네임 2~24자, 댓글 2~1000자를 입력해 주세요." }, 400, origin, env);
  }
  // Hidden honeypot: don't announce rejection to spam bots.
  if (body.website) return reply({ status: "pending", message: "등록 접수되었습니다." }, 202, origin, env);
  const ip = request.headers.get("CF-Connecting-IP") || "";
  if (!ip) return reply({ error: "댓글 등록 환경을 확인할 수 없습니다." }, 403, origin, env);
  const valid = await captchaOkay(body.turnstile_token, ip, env);
  if (!valid) return reply({ error: "스팸 방지 확인을 다시 진행해 주세요." }, 400, origin, env);
  const ipHash = await hashIp(ip, env.COMMENT_HASH_SALT);
  const recent = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM comments WHERE ip_hash = ? AND created_at >= datetime('now', '-10 minutes')"
  ).bind(ipHash).first();
  const daily = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM comments WHERE ip_hash = ? AND created_at >= datetime('now', '-24 hours')"
  ).bind(ipHash).first();
  if (Number(recent?.n || 0) >= 3 || Number(daily?.n || 0) >= 12) {
    return reply({ error: "등록 횟수가 많습니다. 나중에 다시 시도해 주세요." }, 429, origin, env);
  }
  const identical = await env.DB.prepare(
    "SELECT id FROM comments WHERE post_key = ? AND ip_hash = ? AND content = ? AND created_at >= datetime('now', '-24 hours') LIMIT 1"
  ).bind(key, ipHash, message).first();
  if (identical) return reply({ error: "같은 내용을 이미 등록했습니다." }, 409, origin, env);
  const id = crypto.randomUUID();
  await env.DB.prepare(
    "INSERT INTO comments(id,post_key,nickname,content,status,created_at,ip_hash) VALUES(?,?,?,?, 'pending', datetime('now'), ?)"
  ).bind(id, key, name, message, ipHash).run();
  return reply({ status: "pending", message: "댓글이 접수됐습니다. 관리자 승인 후 공개됩니다." }, 202, origin, env);
}

function adminAuthorized(request, env) {
  const raw = request.headers.get("Authorization") || "";
  const expected = "Bearer " + env.ADMIN_TOKEN;
  // Equal lengths and constant-time-ish comparison, avoiding early exit.
  if (raw.length !== expected.length) return false;
  let unequal = 0;
  for (let i = 0; i < raw.length; ++i) unequal |= raw.charCodeAt(i) ^ expected.charCodeAt(i);
  return unequal === 0;
}

async function adminList(url, env, origin) {
  const status = url.searchParams.get("status") || "pending";
  if (!["pending", "approved", "rejected"].includes(status))
    return reply({ error: "잘못된 상태입니다." }, 400, origin, env);
  const result = await env.DB.prepare(
    "SELECT id, post_key, nickname, content, status, created_at FROM comments WHERE status = ? ORDER BY created_at DESC LIMIT 100"
  ).bind(status).all();
  return reply({ comments: result.results || [] }, 200, origin, env);
}

async function adminModerate(request, id, env, origin) {
  if (!/^[a-f0-9-]{36}$/i.test(id)) return reply({ error: "잘못된 댓글 ID" }, 400, origin, env);
  let payload;
  try { payload = await request.json(); } catch { return reply({ error: "잘못된 요청" }, 400, origin, env); }
  const action = payload?.action;
  if (action === "delete") {
    const result = await env.DB.prepare("DELETE FROM comments WHERE id = ?").bind(id).run();
    return reply({ ok: true, deleted: result.meta?.changes || 0 }, 200, origin, env);
  }
  if (action !== "approve" && action !== "reject")
    return reply({ error: "지원하지 않는 처리 방식" }, 400, origin, env);
  const updated = action === "approve" ? "approved" : "rejected";
  const result = await env.DB.prepare(
    "UPDATE comments SET status = ?, reviewed_at = datetime('now') WHERE id = ?"
  ).bind(updated, id).run();
  return reply({ ok: true, updated: result.meta?.changes || 0 }, 200, origin, env);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: origin === (env.ALLOWED_ORIGIN || "https://raspos.github.io") ? 204 : 403,
        headers: cors(origin, env),
      });
    }
    const url = new URL(request.url);
    if (url.pathname === "/health" && request.method === "GET")
      return reply({ status: "ok", storage: !!env.DB }, 200, origin, env);
    if (!env.DB) return reply({ error: "댓글 서비스가 준비되지 않았습니다." }, 503, origin, env);
    if (url.pathname === "/api/comments" && request.method === "GET") {
      try { return await listComments(url, env, origin); }
      catch { return reply({ error: "댓글을 불러올 수 없습니다." }, 503, origin, env); }
    }
    if (url.pathname === "/api/comments" && request.method === "POST") {
      try {
        assertConfig(env);
        return await submitComment(request, env, origin);
      } catch { return reply({ error: "댓글 등록이 지연되고 있습니다." }, 503, origin, env); }
    }
    if (url.pathname.startsWith("/api/admin/")) {
      if (!env.ADMIN_TOKEN || !adminAuthorized(request, env))
        return reply({ error: "관리자 인증이 필요합니다." }, 401, origin, env);
      try {
        if (url.pathname === "/api/admin/comments" && request.method === "GET")
          return await adminList(url, env, origin);
        const match = url.pathname.match(/^\/api\/admin\/comments\/([a-f0-9-]{36})$/i);
        if (match && request.method === "POST") return await adminModerate(request, match[1], env, origin);
      } catch { return reply({ error: "관리자 처리 중 오류가 발생했습니다." }, 503, origin, env); }
    }
    return reply({ error: "존재하지 않는 요청입니다." }, 404, origin, env);
  }
};
