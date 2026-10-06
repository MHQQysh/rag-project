"""Build the standalone reading edition from the accompanying Markdown chapters."""
from pathlib import Path
import html
import re
import json

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent

def inline(text):
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)

def render(text, chapter):
    lines = text.splitlines()
    out = []
    i = 0
    headings = []
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            language = line[3:] or '结构示意'
            body = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                body.append(lines[i]); i += 1
            out.append('<div class="code-label">'+html.escape(language)+'</div><pre><code>'+html.escape('\n'.join(body))+'</code></pre>')
        elif line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            label = line[level:].strip()
            anchor = f'c{chapter}-h{len(headings)}'
            headings.append((level, label, anchor))
            out.append(f'<h{level} id="{anchor}">{inline(label)}</h{level}>')
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                    rows.append(cells)
                i += 1
            out.append('<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+inline(x)+'</th>' for x in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(x)+'</td>' for x in row)+'</tr>' for row in rows[1:])+'</tbody></table></div>')
            continue
        elif line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].startswith('- '):
                items.append('<li>'+inline(lines[i][2:])+'</li>'); i += 1
            out.append('<ul>'+''.join(items)+'</ul>')
            continue
        else:
            body = [line]
            while i+1 < len(lines) and lines[i+1].strip() and not lines[i+1].startswith(('#','|','- ','```')):
                i += 1; body.append(lines[i])
            out.append('<p>'+inline(' '.join(body))+'</p>')
        i += 1
    return '\n'.join(out), headings

chapters = sorted(ROOT.glob('0*.md'))
parts, nav = [], []
for index, file in enumerate(chapters, 1):
    content, headings = render(file.read_text(encoding='utf-8'), index)
    nav.append(f'<a href="#chapter{index}" class="chapter-link"><span>0{index}</span>{html.escape(headings[0][1])}</a>')
    nav.extend(f'<a class="sub" href="#{anchor}">{html.escape(label)}</a>' for level,label,anchor in headings if level==2)
    parts.append(f'<article id="chapter{index}"><div class="chapter-kicker">CHAPTER 0{index}</div>{content}<p class="chapter-end">本章源文件：<a href="{file.name}">{file.name}</a></p></article>')

css = '''
:root{--ink:#192a32;--muted:#677780;--accent:#16766d;--line:#dce4e6;--paper:#fff;--bg:#f4f6f6}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:30px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.9 "Segoe UI","Microsoft YaHei",sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}aside{position:fixed;inset:0 auto 0 0;width:282px;padding:28px 22px;background:#fff;border-right:1px solid var(--line);overflow:auto}
.brand{font-size:14px;letter-spacing:2px;font-weight:800;color:var(--accent)}.nav-intro{font-size:12px;color:var(--muted);margin:7px 0 24px}.chapter-link{display:block;font-weight:700;font-size:14px;line-height:1.65;padding:15px 0 7px;color:var(--ink)}.chapter-link span{display:block;font-size:11px;letter-spacing:2px;color:var(--accent)}.sub{display:block;font-size:12px;line-height:1.65;color:var(--muted);padding:4px 0 4px 13px;border-left:1px solid var(--line)}
main{margin-left:282px;max-width:1270px;padding:42px 54px 90px}.masthead{display:flex;justify-content:space-between;gap:16px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:16px;color:var(--muted);font-size:12px;letter-spacing:1px}button{font:inherit;border:1px solid var(--line);background:white;border-radius:6px;padding:7px 14px;cursor:pointer;color:var(--ink)}button:hover{border-color:var(--accent)}
.intro{padding:40px 0 20px}.intro h1{font-size:38px;line-height:1.3;margin:12px 0 18px;letter-spacing:-1px}.intro p{max-width:760px;color:var(--muted)}.eyebrow,.chapter-kicker{color:var(--accent);font-size:11px;font-weight:800;letter-spacing:2px}.route{display:flex;align-items:stretch;gap:8px;margin:22px 0 30px;flex-wrap:wrap}.route div{flex:1;min-width:110px;background:white;border-top:3px solid var(--accent);padding:14px;font-size:13px}.route small{display:block;color:var(--muted);font-size:11px}.route b{font-weight:600}.route .arrow{flex:0;min-width:0;background:none;border:0;padding:16px 0;color:#8d9c9d}
article{background:var(--paper);border:1px solid var(--line);padding:42px 48px;margin:28px 0;scroll-margin-top:20px}article h1{font-size:28px;line-height:1.4;margin:10px 0 26px}h2{font-size:21px;margin:38px 0 14px;line-height:1.5}h3{font-size:17px;margin:25px 0 10px}p{margin:13px 0}li{padding:0 0 12px 4px}ul{padding-left:21px}strong{font-weight:700}#chapter1>p:nth-of-type(2){color:var(--accent);font-size:14px}#chapter1 li{font-size:15px;line-height:1.85}
code{font:0.87em/1.65 Consolas,"Microsoft YaHei",monospace;background:#eef3f3;padding:2px 5px;overflow-wrap:anywhere;color:#245b59}pre{margin:0 0 22px;padding:20px;background:#f2f5f5;border:1px solid var(--line);overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;line-height:1.75}pre code{background:none;padding:0;color:var(--ink)}.code-label{font:11px/1.5 Consolas,sans-serif;color:var(--muted);margin:20px 0 5px}.table-scroll{overflow:auto;margin:22px 0}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.7}th{background:#eaf1f1;font-weight:600;text-align:left}th,td{border:1px solid var(--line);padding:11px 12px;vertical-align:top}tbody tr:nth-child(even){background:#fafcfc}.chapter-end{border-top:1px solid var(--line);padding-top:18px;margin-top:35px;color:var(--muted);font-size:12px}.footer{font-size:12px;color:var(--muted)}
@media(min-width:1500px){main{margin-left:max(282px,calc((100vw - 1150px)/2));max-width:1120px}}
@media(max-width:950px){aside{width:230px;padding:20px 16px}main{margin-left:230px;padding:25px}article{padding:28px}.intro h1{font-size:30px}}
@media(max-width:700px){aside{position:relative;width:100%;max-height:260px;border-right:0;border-bottom:1px solid var(--line)}aside .sub{display:none}.chapter-link{display:inline-block;margin-right:18px;padding:5px 0}.chapter-link span{display:inline;margin-right:6px}main{margin:0;padding:18px 12px}article{padding:24px 20px}.intro h1{font-size:28px}.route .arrow{display:none}.masthead{letter-spacing:0}body{font-size:15px}h2{font-size:20px}}
@media print{body{background:white;font-size:10.5pt;line-height:1.7}aside,.masthead button,.chapter-end{display:none}main{margin:0;padding:0;max-width:none}.intro{padding:15px 0}article{border:0;padding:0;margin:0;break-before:page}h1,h2,h3{break-after:avoid}tr,pre{break-inside:avoid}a{color:inherit}table{font-size:9pt}.table-scroll{overflow:visible}.route{margin-bottom:10px}@page{size:A4;margin:20mm}}
'''
page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DB-GPT 企业经营分析项目讲解</title><style>'+css+'</style></head><body><aside><div class="brand">DB-GPT / CODE GUIDE</div><div class="nav-intro">从技术总述到每一项计算依据</div>'+''.join(nav)+'</aside><main><header class="masthead"><span>代码讲解手册 · 2026.10.06 · 架构与云端部署版</span><button onclick="window.print()">打印 / 保存 PDF</button></header><section class="intro"><div class="eyebrow">ARCHITECTURE · LOGIC · EVIDENCE</div><h1>把一次经营分析<br>讲到每个数字都有来处</h1><p>先用一页技术总述建立全貌，再沿着真实请求进入代码：谁选择工具、谁核对 SQL、谁计算贡献，以及结果为什么值得相信。</p><div class="route"><div><small>01 / 任务</small><b>官方 Agent 调度</b></div><span class="arrow">→</span><div><small>02 / 约束</small><b>固定指标口径</b></div><span class="arrow">→</span><div><small>03 / 验证</small><b>SQL 与明细对账</b></div><span class="arrow">→</span><div><small>04 / 解释</small><b>贡献与证据</b></div></div></section>'+''.join(parts)+'<footer class="footer">依据本地项目源码与已保存验证记录编写。所有演示金额来自模拟数据。Markdown 章节可独立编辑，本页面不加载外部字体、脚本或服务。</footer></main></body></html>'
(ROOT/'项目讲解.html').write_text(page,encoding='utf-8')

# Check the numeric explanation directly against saved evidence, without model calls.
fixtures = json.loads((PROJECT/'web/assets/expected.json').read_text(encoding='utf-8'))
a=next(f['analysis'] for f in fixtures if f['params']['region']=='华东' and f['params']['current_start']=='2026-08-01')
assert a['delta_cents']==-9900000
assert [f['cents']/100 for f in a['factors']]==[-44800,-32775,-13425,-8000]
from fractions import Fraction
expected=[[-50000,-30000,-11000],[-50000,-28200,-12800],[-42500,-37500,-11000],[-39750,-37500,-13750],[-46800,-28200,-16000],[-39750,-35250,-16000]]
for steps, row in zip(a['permutations'],expected):
    got=[None]*3
    for step in steps:
        got[step['factor']]=Fraction(step['marginal_cents_exact'])/100
    assert got==row, (got,row)
print(f'Built {len(chapters)}-chapter reading edition; six permutation rows and contribution totals match saved evidence.')
