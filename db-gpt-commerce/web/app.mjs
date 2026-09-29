import {
  parameters,
  referenceRows,
  validateRows,
  decompose,
  guardSQL,
  STANDARD_SQL,
} from "./core.mjs";
import { generateSQL } from "./model.mjs";
const $ = (id) => document.getElementById(id);
let dataset,
  running = false,
  controller,
  result;
const money = (x) =>
  x === null
    ? "—"
    : new Intl.NumberFormat("zh-CN", {
        style: "currency",
        currency: "CNY",
        minimumFractionDigits: 2,
      }).format(x / 100);
const number = (x) => new Intl.NumberFormat("zh-CN").format(x);
const percent = (x) =>
  x === null ? "不可定义" : `${x > 0 ? "+" : ""}${x.toFixed(2)}%`;
function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function status(text, error = false) {
  $("status").textContent = text;
  $("status").classList.toggle("error", error);
}
function step(n) {
  [...$("steps").children].forEach((item, i) =>
    item.classList.toggle("active", i <= n),
  );
}
function busy(on) {
  running = on;
  for (const id of ["baseline", "live", "region", "month", "model", "api-key"])
    $(id).disabled = on || !dataset;
  $("cancel").hidden = !on;
}
function question() {
  $("question").textContent =
    `分析 ${$("month").value.replace("-", " 年 ")} 月${$("region").value}地区净收入变化，拆解订单量、渠道结构、渠道内客单价和退款贡献。`;
}
for (const id of ["month", "region"])
  $(id).addEventListener("change", () => {
    question();
    $("results").hidden = true;
    $("empty").hidden = false;
    result = null;
    $("attempts").replaceChildren(el("p", "范围已更改，请重新运行。", "muted"));
    status("已更改分析范围，请运行新的分析。");
    step(-1);
  });
$("clear-key").addEventListener("click", () => {
  $("api-key").value = "";
  status(
    running
      ? "输入框中的 Key 已清除；进行中的请求可点击取消。"
      : "Key 已从页面清除。",
  );
});
$("cancel").addEventListener("click", () => controller?.abort());

function executeQuery(sql, params, signal) {
  guardSQL(sql);
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("./query-worker.js", import.meta.url));
    let finished = false;
    const done = (error, rows) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      worker.terminate();
      signal?.removeEventListener("abort", abort);
      error ? reject(error) : resolve(rows);
    };
    const abort = () => done(Error("分析已取消"));
    const timer = setTimeout(
      () => done(Error("SQL 查询超过 8 秒预算，已终止工作线程")),
      8000,
    );
    if (signal?.aborted) {
      abort();
      return;
    }
    signal?.addEventListener("abort", abort, { once: true });
    worker.onmessage = ({ data }) =>
      done(data.error ? Error(data.error) : null, data.rows);
    worker.onerror = () =>
      done(Error("数据库工作线程加载失败，请刷新页面重试"));
    worker.postMessage({ sql, params, database: dataset.database.slice(0) });
  });
}
function showAttempts(attempts) {
  $("attempts").replaceChildren();
  for (const [i, a] of attempts.entries()) {
    const block = el("details", undefined, "attempt");
    block.open = i === attempts.length - 1;
    block.append(
      el(
        "summary",
        `SQL ${i + 1} · ${a.source === "reference" ? "标准基准" : "DeepSeek 生成"} · ${a.status === "verified" ? "核验通过" : a.status === "rejected" ? "核验未通过" : "待核验"}`,
        `attempt-label ${a.status === "rejected" ? "rejected" : ""}`,
      ),
      el("pre", a.sql),
    );
    if (a.error) block.append(el("p", a.error, "fine"));
    $("attempts").append(block);
  }
}
function display(r) {
  const a = r.analysis,
    p = a.totals.previous,
    c = a.totals.current;
  $("empty").hidden = true;
  $("results").hidden = false;
  $("result-title").textContent =
    `${r.params.region} · ${r.params.current_start.slice(0, 7)} ${r.mode === "live" ? "真实模型分析" : "标准 SQL 基准"}`;
  $("metrics").replaceChildren();
  for (const [label, key] of [
    ["净收入", "net_cents"],
    ["支付订单", "order_count"],
    ["实付客单价", "aov_cents"],
    ["成功退款", "refund_cents"],
  ]) {
    const format = key === "order_count" ? number : money;
    const node = el("div", undefined, "metric");
    node.append(
      el("div", label, "metric-label"),
      el("div", format(c[key]), "metric-value"),
      el("div", `上期 ${format(p[key])}`, "metric-prev"),
    );
    $("metrics").append(node);
  }
  $("delta-summary").textContent =
    `较上期${a.delta_cents < 0 ? "减少" : a.delta_cents > 0 ? "增加" : "持平"} ${money(Math.abs(a.delta_cents))}（${percent(a.change_pct)}）`;
  const max = Math.max(...a.factors.map((f) => Math.abs(f.cents)), 1);
  $("factors").replaceChildren();
  for (const f of a.factors) {
    const row = el("div", undefined, "factor"),
      track = el("div", undefined, "track"),
      bar = el("div", undefined, `bar ${f.cents > 0 ? "positive" : ""}`);
    bar.style.width = `${(Math.abs(f.cents) / max) * 100}%`;
    track.append(bar);
    row.append(
      el("span", f.name),
      track,
      el("span", money(f.cents), "factor-amount"),
    );
    $("factors").append(row);
  }
  $("reconciliation").textContent =
    `✓ 贡献合计与净收入变化完全一致 · 精确分数对账差额 ${money(a.reconciliation_cents)}`;
  $("insights").replaceChildren();
  const facts = [
    [
      `${number(c.order_count - p.order_count)} 单`,
      "支付订单数变化，按支付时间统计。",
    ],
    [
      money(c.aov_cents - p.aov_cents),
      "总体客单价变化，已分配到渠道结构和渠道内客单价两项。",
    ],
    [
      money(c.refund_cents - p.refund_cents),
      "当月成功退款变化，包括更早月份订单在本月的退款。",
    ],
  ];
  for (const [value, text] of facts) {
    const div = el("div", undefined, "insight");
    div.append(el("b", value), el("span", text));
    $("insights").append(div);
  }
  $("channel-rows").replaceChildren();
  for (const channel of a.channels) {
    const row = el("tr");
    row.append(el("td", channel.channel));
    for (const key of [
      "order_count",
      "share_pct",
      "aov_cents",
      "paid_cents",
      "refund_cents",
    ]) {
      const fmt =
        key === "order_count"
          ? number
          : key === "share_pct"
            ? (x) => `${x.toFixed(1)}%`
            : money;
      row.append(
        el(
          "td",
          `${fmt(channel.previous[key])} → ${fmt(channel.current[key])}`,
        ),
      );
    }
    $("channel-rows").append(row);
  }
  $("imputation").textContent =
    a.imputation_notes.join("；") ||
    "本次没有缺失渠道客单价填补。金额单位：人民币元。";
}
async function run(mode) {
  if (running || !dataset) return;
  if (mode === "live" && !$("api-key").value.trim()) {
    $("settings").open = true;
    $("api-key").focus();
    status("请先输入自己的 DeepSeek API Key，或使用无需密钥的基准演示。", true);
    return;
  }
  controller = new AbortController();
  const signal = controller.signal;
  busy(true);
  result = null;
  $("results").hidden = true;
  $("empty").hidden = false;
  $("attempts").replaceChildren();
  const evidence = {
    version: 1,
    engine: "browser-port / sql.js + BigInt rational",
    run_id: crypto.randomUUID(),
    generated_at: new Date().toISOString(),
    mode,
    params: parameters($("month").value, $("region").value),
    provenance: dataset.manifest,
    sql_attempts: [],
    trace: [],
  };
  try {
    step(0);
    status("已固定支付月、成功退款发生月和收货地区口径。");
    evidence.trace.push("resolve");
    const expected = referenceRows(dataset.raw, evidence.params);
    evidence.independent_reference = expected;
    let sql = STANDARD_SQL;
    for (let i = 0; i < (mode === "live" ? 2 : 1); i++) {
      if (signal.aborted) throw Error("分析已取消");
      step(1);
      if (mode === "live") {
        status(
          i
            ? "SQL 未通过核验，正在请求唯一一次修复…"
            : "正在请求 DeepSeek 生成 SQL，通常需要数十秒…",
        );
        const timeout = setTimeout(() => controller.abort(), 90000);
        try {
          const response = await generateSQL({
            key: $("api-key").value,
            model: $("model").value,
            schema: dataset.manifest.schema,
            params: evidence.params,
            previousSQL: i ? sql : undefined,
            error: i ? evidence.sql_attempts.at(-1).error : undefined,
            signal,
          });
          sql = response.sql;
          (evidence.model_calls ??= []).push({
            model: response.model,
            usage: response.usage,
          });
        } finally {
          clearTimeout(timeout);
        }
      }
      const attempt = {
        sql,
        source: mode === "reference" ? "reference" : i ? "live_repair" : "live",
        status: "generated",
      };
      evidence.sql_attempts.push(attempt);
      showAttempts(evidence.sql_attempts);
      try {
        step(2);
        status("正在浏览器内执行 SQLite，并逐项核对订单和退款明细…");
        const rows = await executeQuery(sql, evidence.params, signal);
        validateRows(rows, expected);
        attempt.status = "verified";
        attempt.rows = rows;
        showAttempts(evidence.sql_attempts);
        evidence.rows = rows;
        break;
      } catch (error) {
        attempt.status = "rejected";
        attempt.error = error.message;
        showAttempts(evidence.sql_attempts);
        if (signal.aborted || mode !== "live" || i === 1) throw error;
      }
    }
    if (signal.aborted) throw Error("分析已取消");
    step(3);
    evidence.trace.push("generate_sql", "verify_sql");
    evidence.analysis = decompose(evidence.rows);
    evidence.trace.push("attribute_change");
    evidence.status = "verified";
    result = evidence;
    display(result);
    status("分析完成：SQL 结果通过独立明细核验，四项贡献精确对账。");
  } catch (error) {
    evidence.status = signal.aborted ? "cancelled" : "failed";
    evidence.error = error.message;
    result = evidence;
    status(
      `${error.message}。本次未生成成功报告，也没有用基准结果替代。`,
      true,
    );
    const button = el("button", "下载本次失败证据", "secondary");
    button.addEventListener("click", download);
    $("attempts").append(button);
  } finally {
    busy(false);
    controller = null;
  }
}
function download() {
  if (!result) return;
  const content = JSON.stringify(result, null, 2),
    blob = new Blob([content], { type: "application/json;charset=utf-8" }),
    url = URL.createObjectURL(blob),
    a = el("a");
  a.href = url;
  a.download = `commerce-${result.run_id}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("download").addEventListener("click", download);
$("baseline").addEventListener("click", () => run("reference"));
$("live").addEventListener("click", () => run("live"));
async function initialize() {
  busy(false);
  try {
    const load = async (path) => {
      const r = await fetch(new URL(path, import.meta.url));
      if (!r.ok) throw Error("静态数据加载失败");
      return r;
    };
    const [manifest, raw, database] = await Promise.all([
      load("./assets/manifest.json").then((r) => r.json()),
      load("./assets/raw.json").then((r) => r.json()),
      load("./assets/synthetic.sqlite").then((r) => r.arrayBuffer()),
    ]);
    const hash = [
      ...new Uint8Array(await crypto.subtle.digest("SHA-256", database)),
    ]
      .map((x) => x.toString(16).padStart(2, "0"))
      .join("");
    if (hash !== manifest.database_sha256) throw Error("模拟数据库指纹不一致");
    dataset = { manifest, raw, database };
    $("provenance").textContent = JSON.stringify(manifest, null, 2);
    busy(false);
    status("模拟数据库已就绪。可直接运行基准演示，或输入 Key 使用 DeepSeek。");
  } catch (error) {
    status(
      `${error.message}。请使用 HTTP 服务器或已部署的 Pages 链接打开页面。`,
      true,
    );
  }
}
initialize();
