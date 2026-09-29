export const STANDARD_SQL = `WITH periods(period,start_at,end_at) AS (
SELECT 'previous', :previous_start, :current_start UNION ALL SELECT 'current', :current_start, :end
), payments AS (
SELECT p.period,o.channel_id,COUNT(*) order_count,SUM(o.paid_cents) paid_cents
FROM periods p JOIN orders o ON o.paid_at>=p.start_at AND o.paid_at<p.end_at
WHERE o.status='paid' AND o.shipping_region=:region GROUP BY p.period,o.channel_id
), successful_refunds AS (
SELECT p.period,o.channel_id,SUM(r.amount_cents) refund_cents
FROM periods p JOIN refunds r ON r.refunded_at>=p.start_at AND r.refunded_at<p.end_at
JOIN orders o ON o.order_id=r.order_id WHERE r.status='success' AND o.shipping_region=:region
GROUP BY p.period,o.channel_id)
SELECT p.period,c.name channel,COALESCE(a.order_count,0) order_count,
COALESCE(a.paid_cents,0) paid_cents,COALESCE(r.refund_cents,0) refund_cents
FROM periods p CROSS JOIN channels c
LEFT JOIN payments a ON a.period=p.period AND a.channel_id=c.channel_id
LEFT JOIN successful_refunds r ON r.period=p.period AND r.channel_id=c.channel_id
ORDER BY p.period,c.channel_id`;

export function parameters(month, region) {
  if (
    !["2026-07", "2026-08"].includes(month) ||
    !["华东", "华北"].includes(region)
  )
    throw Error("请选择支持的月份与地区");
  const m = Number(month.slice(-2));
  return {
    previous_start: `2026-${String(m - 1).padStart(2, "0")}-01`,
    current_start: `${month}-01`,
    end: `2026-${String(m + 1).padStart(2, "0")}-01`,
    region,
  };
}

// Conservative lexical gate, not a full SQL parser or a server authorization boundary.
export function guardSQL(sql) {
  if (typeof sql !== "string" || !sql.trim() || sql.length > 20000)
    throw Error("SQL 必须是最多 20000 字符的查询");
  let clean = "",
    state = "plain";
  for (let i = 0; i < sql.length; i++) {
    const a = sql[i],
      b = sql[i + 1];
    if (state === "line") {
      if (a === "\n") {
        state = "plain";
        clean += " ";
      }
      continue;
    }
    if (state === "block") {
      if (a === "*" && b === "/") {
        i++;
        state = "plain";
        clean += " ";
      }
      continue;
    }
    if (state === "string") {
      if (a === "'") {
        if (b === "'") i++;
        else state = "plain";
      }
      continue;
    }
    if (a === "-" && b === "-") {
      state = "line";
      i++;
      continue;
    }
    if (a === "/" && b === "*") {
      state = "block";
      i++;
      continue;
    }
    if (a === "'") {
      state = "string";
      clean += " ";
      continue;
    }
    clean += a;
  }
  if (["block", "string"].includes(state))
    throw Error("SQL 字符串或注释未闭合");
  clean = clean.trim().replace(/;\s*$/, "");
  if (clean.includes(";") || !/^(select|with)\b/i.test(clean))
    throw Error("只允许一条 SELECT / WITH 查询");
  if (
    /\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|load_extension|writefile|readfile|sqlite_master|sqlite_schema|randomblob|zeroblob)\b/i.test(
      clean,
    )
  )
    throw Error("查询包含不允许的操作或系统访问");
  return sql;
}

export function referenceRows(raw, p) {
  const orders = new Map(raw.orders.map((o) => [o.order_id, o])),
    rows = [];
  for (const [period, start, end] of [
    ["previous", p.previous_start, p.current_start],
    ["current", p.current_start, p.end],
  ]) {
    for (const channel of raw.channels) {
      const row = {
        period,
        channel: channel.name,
        order_count: 0,
        paid_cents: 0,
        refund_cents: 0,
      };
      for (const o of raw.orders)
        if (
          o.status === "paid" &&
          o.shipping_region === p.region &&
          o.channel_id === channel.channel_id &&
          o.paid_at >= start &&
          o.paid_at < end
        ) {
          row.order_count++;
          row.paid_cents += o.paid_cents;
        }
      for (const r of raw.refunds) {
        const o = orders.get(r.order_id);
        if (
          o &&
          r.status === "success" &&
          r.refunded_at >= start &&
          r.refunded_at < end &&
          o.shipping_region === p.region &&
          o.channel_id === channel.channel_id
        )
          row.refund_cents += r.amount_cents;
      }
      rows.push(row);
    }
  }
  return rows;
}

export function validateRows(actual, expected) {
  const cols = [
    "channel",
    "order_count",
    "paid_cents",
    "period",
    "refund_cents",
  ];
  if (!Array.isArray(actual) || actual.length !== expected.length)
    throw Error("查询必须覆盖两期全部渠道，包括零值");
  const seen = new Set();
  for (const r of actual) {
    if (Object.keys(r).sort().join("|") !== cols.join("|"))
      throw Error("查询输出列不符合五列契约");
    const k = JSON.stringify([r.period, r.channel]);
    if (seen.has(k)) throw Error("期间渠道重复");
    seen.add(k);
    for (const c of ["order_count", "paid_cents", "refund_cents"])
      if (!Number.isSafeInteger(r[c]) || r[c] < 0)
        throw Error("计数和金额必须是安全范围内的非负整数分");
    const e = expected.find(
      (e) => e.period === r.period && e.channel === r.channel,
    );
    if (!e || cols.some((c) => e[c] !== r[c]))
      throw Error(
        "独立明细核验不一致：检查支付月、成功退款发生月、地区快照和重复连接",
      );
  }
}

const gcd = (a, b) => (b ? gcd(b, a % b) : a < 0n ? -a : a);
class F {
  constructor(n, d = 1n) {
    n = BigInt(n);
    d = BigInt(d);
    if (!d) throw Error("分母不能为零");
    if (d < 0n) {
      n = -n;
      d = -d;
    }
    const g = gcd(n, d);
    this.n = n / g;
    this.d = d / g;
  }
  add(b) {
    b = F.of(b);
    return new F(this.n * b.d + b.n * this.d, this.d * b.d);
  }
  sub(b) {
    b = F.of(b);
    return this.add(new F(-b.n, b.d));
  }
  mul(b) {
    b = F.of(b);
    return new F(this.n * b.n, this.d * b.d);
  }
  div(b) {
    b = F.of(b);
    return new F(this.n * b.d, this.d * b.n);
  }
  number() {
    return Number(this.n) / Number(this.d);
  }
  exact() {
    return this.d === 1n ? String(this.n) : `${this.n}/${this.d}`;
  }
  static of(x) {
    return x instanceof F ? x : new F(x);
  }
}
export function decompose(rows) {
  const groups = Object.fromEntries(
    ["previous", "current"].map((p) => [
      p,
      Object.fromEntries(
        rows.filter((r) => r.period === p).map((r) => [r.channel, r]),
      ),
    ]),
  );
  const channels = Object.keys(groups.previous).sort(),
    totals = {},
    imputation_notes = [];
  const values = ["previous", "current"].map((p, i) => {
    const list = Object.values(groups[p]),
      order_count = list.reduce((s, r) => s + r.order_count, 0),
      paid_cents = list.reduce((s, r) => s + r.paid_cents, 0),
      refund_cents = list.reduce((s, r) => s + r.refund_cents, 0);
    if (!order_count)
      throw Error("任一整月没有支付订单时，渠道结构与客单价分解不可识别");
    totals[p] = {
      order_count,
      paid_cents,
      refund_cents,
      net_cents: paid_cents - refund_cents,
      aov_cents: paid_cents / order_count,
    };
    const prices = channels.map((c) => {
      const r = groups[p][c],
        other = groups[i === 0 ? "current" : "previous"][c];
      if (r.order_count) return new F(r.paid_cents, r.order_count);
      imputation_notes.push(
        `${p}/${c} 无订单，客单价借用另一期间；两期均无订单取零`,
      );
      return other.order_count
        ? new F(other.paid_cents, other.order_count)
        : new F(0);
    });
    return [
      new F(order_count),
      channels.map((c) => new F(groups[p][c].order_count, order_count)),
      prices,
    ];
  });
  const gross = (v) =>
    v[0].mul(v[1].reduce((s, x, i) => s.add(x.mul(v[2][i])), new F(0)));
  const permutations = [],
    contributions = [new F(0), new F(0), new F(0)];
  for (const order of [
    [0, 1, 2],
    [0, 2, 1],
    [1, 0, 2],
    [1, 2, 0],
    [2, 0, 1],
    [2, 1, 0],
  ]) {
    const state = [...values[0]],
      steps = [];
    let before = gross(state);
    for (const i of order) {
      state[i] = values[1][i];
      const after = gross(state),
        m = after.sub(before);
      contributions[i] = contributions[i].add(m.div(6));
      steps.push({ factor: i, marginal_cents_exact: m.exact() });
      before = after;
    }
    permutations.push(steps);
  }
  contributions.push(
    new F(totals.previous.refund_cents - totals.current.refund_cents),
  );
  const delta_cents = totals.current.net_cents - totals.previous.net_cents;
  if (
    contributions.reduce((s, c) => s.add(c), new F(0)).sub(delta_cents).n !== 0n
  )
    throw Error("贡献对账失败");
  return {
    totals,
    delta_cents,
    change_pct: totals.previous.net_cents
      ? (delta_cents / totals.previous.net_cents) * 100
      : null,
    factors: ["订单量", "渠道结构", "渠道内客单价", "退款变化"].map(
      (name, i) => ({
        name,
        cents: contributions[i].number(),
        exact_cents: contributions[i].exact(),
        share_of_change_pct: delta_cents
          ? contributions[i].div(delta_cents).mul(100).number()
          : null,
      }),
    ),
    channels: channels.map((channel) => ({
      channel,
      ...Object.fromEntries(
        ["previous", "current"].map((p) => {
          const r = groups[p][channel];
          return [
            p,
            {
              ...r,
              share_pct: (r.order_count / totals[p].order_count) * 100,
              aov_cents: r.order_count ? r.paid_cents / r.order_count : null,
              net_cents: r.paid_cents - r.refund_cents,
            },
          ];
        }),
      ),
    })),
    reconciliation_cents: 0,
    permutations,
    imputation_notes,
    interpretation:
      "贡献是指标恒等式的算术分解，不是因果结论。总体客单价已拆分到渠道结构和渠道内客单价，不能重复相加。",
  };
}
