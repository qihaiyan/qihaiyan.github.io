/**
 * Markdown 协商 Worker —— 自建版 Cloudflare "Markdown for Agents"(官方功能需 Pro 套餐)。
 *
 * 作用:对带 Accept: text/markdown 的请求,返回同路径的 .md 静态文件
 * (由 deploy 工作流构建时生成,见 tools/gen-md.py);其余请求原样回源,
 * 浏览器和普通爬虫的行为完全不变。
 *
 * 部署(免费套餐即可,约 2 分钟):
 * 1. Cloudflare 控制台 -> Workers & Pages -> Create -> Worker,
 *    命名如 markdown-agent -> Edit code,粘贴本文件全部内容 -> Deploy。
 * 2. Worker 的 Settings -> Domains & Routes -> Add -> Route:
 *    springcamp.cn/*  (Zone 选 springcamp.cn)。
 * 3. 验证: curl -H "Accept: text/markdown" https://springcamp.cn/spring-mcp/
 *    应返回 Content-Type: text/markdown 的纯正文。
 *
 * 说明:Worker 内 fetch 同 zone 的请求不会再次进入本 Worker(Cloudflare 的
 * 防环机制),因此 fetch(request) 直通回源是安全的;首页、about 等没有
 * 生成 .md 的路径在 404 后自动回退到 HTML。
 */
export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return fetch(request);
    }
    const accept = request.headers.get("accept") || "";
    if (!accept.includes("text/markdown")) {
      return fetch(request);
    }
    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname.startsWith("/cdn-cgi/")) {
      return fetch(request);
    }
    const md = new URL(request.url);
    md.pathname = url.pathname.replace(/\/+$/, "") + ".md";
    const resp = await fetch(md.toString(), {
      method: request.method,
      headers: new Headers(request.headers),
      redirect: "follow",
    });
    if (resp.ok) {
      const headers = new Headers(resp.headers);
      headers.set("content-type", "text/markdown; charset=utf-8");
      headers.set("vary", "Accept"); // 防止中间缓存把 markdown 发给浏览器
      return new Response(resp.body, { status: resp.status, headers });
    }
    return fetch(request);
  },
};
