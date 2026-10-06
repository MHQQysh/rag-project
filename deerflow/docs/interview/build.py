"""Build the offline interview reader and Markdown chapters from questions.json.

Run from any directory: python -X utf8 deerflow/docs/interview/build.py
Only Python's standard library is required. No model/API call is made.
"""

from collections import Counter
from html import escape
import argparse
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--renderer", type=Path, help="Optional path to render-html's render_html.py; refreshes print.html too")
args = parser.parse_args()
DEERFLOW = HERE.parents[1]
REPO = DEERFLOW.parent
BASE = "https://github.com/MHQQysh/rag-project"
bank = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
questions = bank["questions"]
assert len(questions) == 120
assert len({q["question"] for q in questions}) == 120
assert [q["id"] for q in questions] == list(range(1, 121))
assert Counter(q["level"] for q in questions) == {"L1": 48, "L2": 48, "L3": 24}


def source_link(source):
    target = (DEERFLOW / source).resolve()
    relative = target.relative_to(REPO).as_posix()
    assert target.exists(), f"Missing source: {source}"
    kind = "tree" if target.is_dir() else "blob"
    return f"{BASE}/{kind}/main/{quote(relative, safe='/')}"


def markdown_question(q):
    sources = " · ".join(f"[{s}]({source_link(s)})" for s in q["sources"])
    return (
        f"### Q{q['id']:03d} · {q['level']} · {q['question']}\n\n"
        "<details>\n<summary>展开答案与追问</summary>\n\n"
        f"**口述回答：** {q['answer']}\n\n"
        f"**原理与例子：** {q['explanation']}\n\n"
        f"**追问与回答：** {q['followup']}\n\n"
        f"**易错边界：** {q['boundary']}\n\n"
        f"**源码 / 依据：** {sources}\n\n</details>\n"
    )


def card(q):
    sources = "".join(
        f'<a href="{source_link(s)}" target="_blank" rel="noopener noreferrer">{escape(s)}</a>'
        for s in q["sources"]
    )
    return f'''<article class="question" id="q{q['id']:03d}" data-level="{q['level']}" data-chapter="{q['chapter']}">
<div class="qmeta"><span>Q{q['id']:03d} / {q['level']}</span><label><input type="checkbox" class="learned" data-id="{q['id']}"> 已掌握</label></div>
<details><summary>{escape(q['question'])}</summary><div class="answer">
<h4>先这样回答</h4><p>{escape(q['answer'])}</p>
<h4>把逻辑讲透</h4><p>{escape(q['explanation'])}</p>
<div class="follow"><h4>面试官继续追问</h4><p>{escape(q['followup'])}</p></div>
<p class="boundary"><strong>易错边界</strong>　{escape(q['boundary'])}</p>
<div class="sources"><span>源码 / 依据</span>{sources}</div>
</div></details></article>'''


chapters = bank["chapters"]
all_md = [(HERE / "overview.md").read_text(encoding="utf-8")]
toc = []
sections = []
options = []
for chapter in chapters:
    number, title = chapter["id"], chapter["title"]
    qs = [q for q in questions if q["chapter"] == number]
    assert len(qs) == 10
    filename = f"chapter-{number:02d}.md"
    heading = f"## §{number + 7} {title}\n\n"
    body = "\n".join(map(markdown_question, qs))
    (HERE / filename).write_text(
        f"# 第 {number:02d} 章 · {title}\n\n[返回学习入口](README.md)\n\n" + body,
        encoding="utf-8", newline="\n",
    )
    all_md.append(heading + body)
    toc.append(f"| {number:02d} | [{title}]({filename}) | Q{qs[0]['id']:03d}—Q{qs[-1]['id']:03d} |")
    options.append(f'<option value="{number}">{number:02d} · {escape(title)}</option>')
    sections.append(f'<section class="chapter" id="chapter-{number}"><div class="chapterhead"><span>{number:02d}</span><h2>{escape(title)}</h2><small>10 QUESTIONS</small></div>' + "".join(map(card, qs)) + "</section>")

(HERE / "complete-guide.md").write_text("\n\n".join(all_md), encoding="utf-8", newline="\n")
(HERE / "README.md").write_text(
    "# DeerFlow × RAG 项目面试题解\n\n"
    "120 道题，12 个主题；每题包含口述回答、原理、追问、边界和源码依据。不是只列问题的题单。\n\n"
    "- [在线阅读与练习](https://shihongyuan.cn/rag-project/deerflow-interview/)：搜索、章节和难度筛选、随机抽题、已掌握标记。\n"
    "- [先读项目总述](overview.md)：架构、请求链路、个人改动与七天学习顺序。\n"
    "- [完整 Markdown 题解](complete-guide.md)：适合 GitHub 阅读与版本比较。\n"
    "- [打印版 HTML](print.html)：下载后离线打开，可使用浏览器打印为 PDF。\n\n"
    "代码依据为本次导入快照，路径以 deerflow/ 为根；../ 开头指向并列子项目。源码链接指向主分支，后续代码升级应同步复核题解。部署事实以 2026-10-06 文档为准；设计建议不代表已经实现。\n\n"
    "| 章 | 主题 | 题号 |\n| --- | --- | --- |\n" + "\n".join(toc) +
    "\n\n## 维护\n\n修改 questions.json 与 overview.md，再执行 `python -X utf8 deerflow/docs/interview/build.py` 生成章节、完整版和交互页。打印版由 render-html 技能脚本离线渲染；生成记录见 review.json。\n\n"
    "传入 `--renderer /path/to/render_html.py` 可同时更新打印版并展开全部答案。未提供该参数时不会更新 print.html。\n\n"
    "交互页是无外部依赖的单文件 HTML，练习标记只保存于当前浏览器，不上传、不调用模型、不收集账号或 API Key。GitHub Pages 只发布阅读页面；完整 Agent 仍需要后端服务。\n",
    encoding="utf-8", newline="\n",
)

template = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="基于实际源码的 120 道 DeerFlow 与 RAG 面试题解：架构、Agent、沙箱、记忆、流式界面、部署及演示认证。"><title>DeerFlow × RAG · 120 道项目面试题解</title>
<style>
:root{--ink:#193135;--muted:#5b7376;--paper:#f4f3ed;--line:#d4dfd9;--green:#126252;--soft:#eaf1ec}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.85 system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}a{color:var(--green);text-underline-offset:4px}button,input,select{font:inherit}button,select{cursor:pointer}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #cc8b38;outline-offset:3px}[hidden]{display:none!important}.wrap{max-width:1180px;margin:auto;padding:0 32px}.top{padding:23px 0;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:20px;font-size:13px;letter-spacing:1px}.hero{padding:64px 0 40px;display:grid;grid-template-columns:1.65fr 1fr;gap:60px;align-items:center}.eyebrow{color:var(--green);font-size:12px;letter-spacing:3px;font-weight:700}h1{font-size:clamp(36px,5vw,62px);line-height:1.2;letter-spacing:-1.5px;margin:18px 0 25px}h1 span{display:block;color:var(--green)}.lead{max-width:620px;color:var(--muted);font-size:18px}.stats{display:flex;gap:30px;margin:28px 0}.stat b{font-size:31px;display:block;line-height:1.3}.stat small{color:var(--muted)}.map{border:1px solid var(--line);border-radius:16px;background:#fff;padding:28px;box-shadow:8px 10px 0 #e3e8dd}.map h3{margin:0 0 18px;font-size:14px;letter-spacing:1px}.node{background:var(--soft);border:1px solid var(--line);padding:12px 16px;border-radius:8px}.node b{display:block}.node small{color:var(--muted)}.arrow{color:#89a89b;text-align:center;line-height:1.6}.intro{background:#193b38;color:#e6efe9;border-radius:16px;padding:32px;margin:8px 0 28px}.intro h2{font-size:22px;margin:0 0 10px}.intro p{margin:10px 0;color:#d1ded6}.intro a{color:#e6d8a4}.readlinks{display:flex;gap:22px;flex-wrap:wrap;margin:20px 0}.note{font-size:14px;color:var(--muted)}.controls{position:sticky;top:0;background:rgba(244,243,237,.98);border-block:1px solid var(--line);padding:18px 0;z-index:3}.filterrow{display:grid;grid-template-columns:2fr 1.6fr 1fr;gap:12px}.field{display:flex;flex-direction:column;font-size:12px;color:var(--muted);gap:4px}input[type=search],select{width:100%;min-width:0;background:white;border:1px solid #afc3b7;border-radius:7px;padding:10px 12px;color:var(--ink);font-size:15px}.actions{display:flex;align-items:center;gap:10px;margin-top:12px;flex-wrap:wrap}button{border:1px solid #b1c5b9;border-radius:6px;background:#fff;color:var(--ink);padding:6px 12px;font-size:13px}button:hover{background:var(--soft)}.primary{background:var(--green);color:white;border-color:var(--green)}.primary:hover{background:#184c40}#count{margin-left:auto;font-size:13px;color:var(--muted)}.chapter{scroll-margin-top:210px}.chapterhead{display:flex;gap:18px;align-items:baseline;margin:46px 0 18px}.chapterhead>span{font:42px Georgia,serif;color:#86a797}.chapterhead h2{font-size:25px;margin:0}.chapterhead small{margin-left:auto;letter-spacing:2px;color:var(--muted);font-size:10px}.question{border:1px solid var(--line);background:#fff;border-radius:10px;padding:20px 25px;margin:12px 0;scroll-margin-top:215px}.qmeta{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);letter-spacing:1px;margin-bottom:6px}.qmeta label{cursor:pointer;display:flex;gap:5px;align-items:center}.question.mastered{border-left:4px solid #509979}.question summary{cursor:pointer;font-size:19px;font-weight:650;line-height:1.6;padding:5px 0}.answer{margin-top:18px;border-top:1px solid #e6ede7;padding-top:5px}.answer h4{font-size:12px;color:var(--green);letter-spacing:1px;margin:20px 0 5px}.answer p{margin:4px 0 15px}.follow{background:#eef3ef;border-left:3px solid #9ab6a3;padding:4px 18px 1px;border-radius:0 6px 6px 0}.boundary{font-size:14px;color:#776449;background:#faf5e9;border-radius:5px;padding:12px 15px}.sources{border-top:1px dashed var(--line);padding-top:13px;font-size:11px;overflow-wrap:anywhere}.sources span{display:block;color:var(--muted)}.sources a{display:block;font-family:ui-monospace,monospace;margin:3px 0}#empty{padding:50px;text-align:center}.footer{border-top:1px solid var(--line);margin:55px 0 25px;padding-top:24px;color:var(--muted);font-size:13px}.back{position:fixed;bottom:18px;right:18px;background:var(--green);color:#fff;border:0;border-radius:30px;padding:10px 15px;text-decoration:none;font-size:13px}.noscript{background:#fff1cf;padding:15px}.print-hide{}.notice{border:1px solid var(--line);padding:18px;border-radius:8px;margin:25px 0;font-size:14px}
@media(max-width:760px){.wrap{padding:0 18px}.hero{grid-template-columns:1fr;gap:20px;padding-top:34px}.map{display:none}.filterrow{grid-template-columns:1fr 1fr}.field:first-child{grid-column:1/-1}.chapterhead small{display:none}.question{padding:17px}.chapterhead h2{font-size:21px}.stats{gap:24px}.intro{padding:24px}.top{font-size:11px}.controls{position:static}.chapter,.question{scroll-margin-top:15px}#count{width:100%;margin-left:0}.lead{font-size:16px}}
@media print{body{background:white;font-size:11pt}.wrap{max-width:none;padding:0}.controls,.qmeta label,.back,.readlinks,.top,.map,.print-hide{display:none}.hero{display:block;padding:0}h1{font-size:30pt}.stats{margin:10px 0}.intro{background:white;color:#193135;border:1px solid #bbb}.intro p{color:#193135}.chapterhead{break-after:avoid}.question{break-inside:avoid;border-color:#ccc}.question summary{font-size:13pt}.answer{display:block}.answer h4{font-size:10pt}.sources{font-size:8pt}.chapterhead h2{font-size:19pt}.boundary,.follow{background:#f5f5f5}}
</style></head><body id="top"><div class="wrap">
<nav class="top"><strong>RAG PROJECT / ENGINEERING NOTES</strong><a href="https://github.com/MHQQysh/rag-project/tree/main/deerflow">完整项目源码 ↗</a></nav>
<header class="hero"><div><div class="eyebrow">INTERVIEW FIELD GUIDE · 2026.10</div><h1>不只会运行，<span>更要讲清逻辑。</span></h1><p class="lead">DeerFlow × RAG 项目面试题解。从一条用户请求出发，读懂模型、Agent、工具、状态与网页之间的关系。</p><div class="stats"><div class="stat"><b>120</b><small>问题 + 答案 + 追问</small></div><div class="stat"><b>12</b><small>工程主题</small></div><div class="stat"><b>3</b><small>学习层级</small></div></div></div>
<div class="map" aria-label="简化请求流程"><h3>ONE REQUEST, MANY STEPS</h3><div class="node"><b>01 · 页面与 Gateway</b><small>输入、身份、会话、运行</small></div><div class="arrow">↓</div><div class="node"><b>02 · Agent ⇄ 模型</b><small>上下文、决策、工具、子任务</small></div><div class="arrow">↓</div><div class="node"><b>03 · 执行与返回</b><small>沙箱、状态、SSE、文件产物</small></div></div></header>
<section class="intro"><h2>先记住一条主线</h2><p>模型负责生成决策，框架负责组织执行，工具负责产生动作，网页让用户看见和管理这个过程。DeerFlow 是完整的任务执行应用；RAG 可以成为它的一种检索能力。</p><p>你的讲述重点：基于原版完成部署与模型配置、小内存资源适配，以及独立普通演示账号的一键进入。核心 Agent 框架来自上游；同仓库存放 RAG 尚不等于运行时已经打通。</p><a href="print.html">先读总述与完整请求链路 →</a></section>
<div class="readlinks"><a href="print.html">总述 + 全题打印版</a><a href="https://github.com/MHQQysh/rag-project/blob/main/deerflow/docs/interview/complete-guide.md">Markdown 完整版</a><a href="https://github.com/MHQQysh/rag-project/blob/main/deerflow/deploy/ecs/README.md">个人改动与验收记录</a></div>
<p class="note">L1 基础口述 48 题 · L2 工程进阶 48 题 · L3 边界分析 24 题。建议先独立讲 60 秒，再展开答案。源码链接用于定位，设计建议不代表已经完成的功能。</p>
<div class="notice">部署事实以 2026-10-06 记录为准。演示访客共享历史和文件；公网曾出现备案拦截；目前没有高并发或完整多租户生产能力的验证结论。本文阅读页可独立于 Agent 后端使用。</div>
<noscript><p class="noscript">JavaScript 已关闭，仍可逐题展开阅读；搜索、筛选和练习标记需要启用 JavaScript。</p></noscript>
<div class="controls"><div class="filterrow"><label class="field">搜索问题、答案或源码<input id="search" type="search" placeholder="例如：沙箱、SSE、个人贡献、DeepSeek"></label><label class="field">按主题阅读<select id="chapter"><option value="">全部主题</option>__OPTIONS__</select></label><label class="field">学习层级<select id="level"><option value="">全部难度</option><option value="L1">L1 · 基础口述</option><option value="L2">L2 · 工程进阶</option><option value="L3">L3 · 边界分析</option></select></label></div><div class="actions"><button id="random" class="primary">随机抽一题</button><button id="expand">展开当前答案</button><button id="collapse">收起答案</button><button id="reset">清除筛选</button><label class="note"><input id="unlearned" type="checkbox"> 只看未掌握</label><output id="count" aria-live="polite"></output></div></div>
<main>__SECTIONS__<p id="empty" hidden>没有匹配题目，请更换关键词或清除筛选。</p></main>
<footer class="footer">基于实际源码与部署记录编写 · 原版 DeerFlow 遵循其 MIT 许可证 · 练习标记只保存在当前浏览器，不上传数据。<br>公开题库不含账号密码、API Key 或私人聊天数据。源码入口：MHQQysh/rag-project/deerflow。</footer></div><a class="back" href="#top">回到顶部 ↑</a>
<script>
(()=>{'use strict';
const $=id=>document.getElementById(id), cards=[...document.querySelectorAll('.question')], chapters=[...document.querySelectorAll('.chapter')];
const key='deerflow-interview-learned-v1';let saved=[];try{const v=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(v))saved=v.filter(x=>typeof x==='string');}catch{}const learned=new Set(saved);
const text=new Map(cards.map(c=>[c,c.textContent.toLowerCase()]));const visible=()=>cards.filter(c=>!c.hidden);
function filter(){const term=$('search').value.trim().toLowerCase(), level=$('level').value,chapter=$('chapter').value;cards.forEach(c=>{const known=learned.has(c.querySelector('.learned').dataset.id);c.classList.toggle('mastered',known);c.hidden=!!((term&&!text.get(c).includes(term))||(level&&c.dataset.level!==level)||(chapter&&c.dataset.chapter!==chapter)||($('unlearned').checked&&known));});chapters.forEach(c=>c.hidden=![...c.querySelectorAll('.question')].some(q=>!q.hidden));const n=visible().length;$('empty').hidden=n!==0;$('count').textContent=`显示 ${n} / 120 题 · 已掌握 ${cards.filter(c=>learned.has(c.querySelector('.learned').dataset.id)).length} 题`;}
cards.forEach(c=>{const box=c.querySelector('.learned');box.checked=learned.has(box.dataset.id);box.addEventListener('change',()=>{box.checked?learned.add(box.dataset.id):learned.delete(box.dataset.id);try{localStorage.setItem(key,JSON.stringify([...learned]));}catch{}filter();});});
['search','chapter','level','unlearned'].forEach(id=>$(id).addEventListener('input',filter));
$('expand').addEventListener('click',()=>visible().forEach(c=>c.querySelector('details').open=true));$('collapse').addEventListener('click',()=>cards.forEach(c=>c.querySelector('details').open=false));
$('reset').addEventListener('click',()=>{['search','chapter','level'].forEach(id=>$(id).value='');$('unlearned').checked=false;filter();});
$('random').addEventListener('click',()=>{const list=visible();if(!list.length)return;const c=list[Math.floor(Math.random()*list.length)];c.querySelector('details').open=false;c.scrollIntoView({behavior:'smooth',block:'start'});c.querySelector('summary').focus({preventScroll:true});history.replaceState(null,'','#'+c.id);});
let beforePrint=[];window.addEventListener('beforeprint',()=>{beforePrint=cards.map(c=>c.querySelector('details').open);cards.forEach(c=>c.querySelector('details').open=true);});window.addEventListener('afterprint',()=>cards.forEach((c,i)=>c.querySelector('details').open=beforePrint[i]||false));filter();
if(/^#q\d{3}$/.test(location.hash)){const target=document.getElementById(location.hash.slice(1));if(target){target.querySelector('details').open=true;target.scrollIntoView();}}
})();
</script></body></html>'''
(HERE / "index.html").write_text(
    template.replace("__OPTIONS__", "".join(options)).replace("__SECTIONS__", "".join(sections)),
    encoding="utf-8", newline="\n",
)
print(f"Built {len(questions)} questions, {len(chapters)} chapters; all source paths exist.")
if args.renderer:
    subprocess.run([
        sys.executable, "-X", "utf8", str(args.renderer.resolve()),
        "deerflow/docs/interview/complete-guide.md", "--template", "academic",
        "--out", "deerflow/docs/interview/print.html", "--title", "DeerFlow × RAG 项目面试题解",
        "--subtitle", "框架总述 · 120 道问题与答案 · 源码定位 · 工程取舍",
        "--eyebrow", "INTERVIEW PREP · DEERFLOW", "--author", "RAG Project",
        "--lang", "zh-CN", "--offline",
    ], cwd=REPO, check=True)
    output = HERE / "print.html"
    markup = output.read_text(encoding="utf-8").replace("<details>", "<details open>")
    output.write_text("\n".join(line.rstrip() for line in markup.splitlines()) + "\n", encoding="utf-8", newline="\n")
else:
    print("print.html was not refreshed; pass --renderer to regenerate it.")
