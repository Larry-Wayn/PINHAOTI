"""The self-contained browser interface for the local paper builder."""

import html


CSS = """
:root {
  color-scheme: light;
  --paper: #ffffff;
  --canvas: #f6f7f4;
  --ink: #1d2925;
  --muted: #65736c;
  --line: #dde5df;
  --green: #276c5b;
  --green-dark: #19503f;
  --green-soft: #e9f2ec;
  --serif: Georgia, 'Songti SC', 'STSong', serif;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; background: var(--canvas); color: var(--ink); }
button, select, textarea { font: inherit; }
button, a, select, textarea { -webkit-tap-highlight-color: transparent; }
:focus-visible { outline: 3px solid #7db4a2; outline-offset: 3px; }
.skip-link { position: absolute; left: 20px; top: -80px; z-index: 10; padding: 10px 14px;
  border-radius: 9px; background: var(--ink); color: white; }
.skip-link:focus { top: 12px; }
.shell { max-width: 1312px; margin: 0 auto; padding: 0 40px; }
.site-header { display: flex; align-items: center; justify-content: space-between;
  gap: 18px; min-height: 82px; border-bottom: 1px solid var(--line); }
.brand { display: inline-flex; align-items: center; gap: 12px; color: var(--ink);
  text-decoration: none; white-space: nowrap; }
.brand-mark { display: grid; grid-template-columns: repeat(2, 9px); gap: 3px;
  padding: 8px; border-radius: 11px; background: var(--green); transform: rotate(-5deg); }
.brand-mark i { width: 9px; height: 9px; border-radius: 2px; background: white; opacity: .92; }
.brand-mark i:nth-child(2) { opacity: .46; }
.brand-mark i:nth-child(3) { opacity: .68; }
.brand-name { font-size: 19px; font-weight: 760; letter-spacing: -.04em; }
.brand-divider { width: 1px; height: 18px; background: #cbd5cd; margin: 0 1px; }
.brand-sub { color: var(--muted); font-size: 12px; letter-spacing: .12em; }
.header-meta { display: flex; align-items: center; gap: 12px; color: var(--muted); font-size: 12px; }
.status { display: inline-flex; align-items: center; gap: 7px; padding: 8px 11px;
  border: 1px solid #cfe3d4; border-radius: 999px; background: #edf6ef;
  color: #306848; font-weight: 650; }
.status::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #4d9d64; }
.hero { display: flex; justify-content: space-between; align-items: end; gap: 32px;
  padding: 68px 0 47px; }
.hero-copy { max-width: 740px; }
.eyebrow { display: flex; align-items: center; gap: 10px; color: var(--green);
  font-size: 11px; font-weight: 760; letter-spacing: .18em; }
.eyebrow::before { content: ''; display: block; width: 24px; height: 2px; background: currentColor; }
h1 { margin: 17px 0 15px; font-size: clamp(33px, 4vw, 51px); line-height: 1.22;
  letter-spacing: -.055em; font-weight: 770; }
h1 span { color: var(--green); }
.hero p { max-width: 610px; margin: 0; color: var(--muted); font-size: 15px; line-height: 1.8; }
.hero-stat { flex: 0 0 auto; min-width: 186px; padding: 18px 0 5px 24px;
  border-left: 1px solid #cbd9ce; }
.hero-stat strong { display: block; font-family: var(--serif); color: var(--ink);
  font-size: 35px; font-weight: 500; letter-spacing: -.045em; line-height: 1; }
.hero-stat small { display: block; margin-top: 12px; color: var(--muted); font-size: 12px; }
.workspace { display: grid; grid-template-columns: minmax(345px, .85fr) minmax(0, 1.15fr);
  align-items: start; gap: 22px; padding-bottom: 35px; }
.card { min-width: 0; border: 1px solid var(--line); border-radius: 20px; background: var(--paper);
  box-shadow: 0 13px 35px rgba(29, 54, 37, .035); }
.builder { padding: 30px; }
.panel-kicker { display: inline-flex; align-items: center; gap: 9px; color: var(--green);
  font-size: 11px; font-weight: 760; letter-spacing: .15em; text-transform: uppercase; }
.panel-kicker::before { content: ''; width: 18px; height: 1px; background: currentColor; }
.panel-title { margin: 11px 0 0; font-size: 23px; letter-spacing: -.04em; line-height: 1.35; }
.panel-intro { margin: 8px 0 0; color: var(--muted); font-size: 13px; line-height: 1.7; }
.field-header { display: flex; justify-content: space-between; align-items: baseline; gap: 8px;
  margin: 30px 0 10px; }
.field-header label, .select-block label { color: var(--ink); font-size: 13px; font-weight: 720; }
.field-header small { color: #8b9690; font-size: 11px; white-space: nowrap; }
textarea { display: block; width: 100%; min-height: 266px; padding: 16px 17px;
  resize: vertical; border: 1px solid #cfdad2; border-radius: 12px; outline: none;
  background: #fbfcfa; color: var(--ink); font-size: 14px; line-height: 1.8;
  transition: background .2s, border-color .2s, box-shadow .2s; }
textarea::placeholder { color: #a2aca4; opacity: 1; }
textarea:focus { border-color: #75a58e; background: white;
  box-shadow: 0 0 0 4px rgba(87, 143, 110, .1); }
.input-help { margin: 11px 0 0; color: var(--muted); font-size: 12px; line-height: 1.7; }
.input-help code { padding: 3px 6px; border-radius: 5px; background: #f0f4ee;
  color: #315b45; font-size: 11px; }
.alert { margin-top: 15px; padding: 12px 14px; border: 1px solid #efc9bf;
  border-radius: 10px; background: #fff5f2; color: #a44334; font-size: 13px; line-height: 1.6; }
.form-bottom { display: grid; grid-template-columns: 1fr auto; align-items: end;
  gap: 14px; margin-top: 29px; padding-top: 23px; border-top: 1px solid #edf0eb; }
.select-block { min-width: 0; }
.select-block label { display: block; margin-bottom: 9px; }
select { width: 100%; min-width: 160px; min-height: 45px; padding: 0 30px 0 13px;
  border: 1px solid #cfdad2; border-radius: 9px; background: white; color: var(--ink);
  cursor: pointer; }
.primary { display: inline-flex; justify-content: center; align-items: center; gap: 15px;
  min-height: 45px; padding: 0 20px; border: 1px solid var(--green); border-radius: 9px;
  background: var(--green); color: white; font-size: 13px; font-weight: 720;
  white-space: nowrap; cursor: pointer; transition: transform .2s, background .2s, box-shadow .2s; }
.primary:hover { transform: translateY(-1px); background: var(--green-dark);
  box-shadow: 0 7px 15px rgba(31, 90, 69, .15); }
.primary .arrow { font-size: 17px; line-height: 0; font-weight: 400; }
.local-note { display: flex; align-items: start; gap: 9px; margin-top: 27px; padding: 12px 13px;
  border-radius: 9px; background: #f4f7f1; color: #65756a; font-size: 11px; line-height: 1.65; }
.local-note b { color: #4b8061; font-size: 14px; line-height: 1.1; }
.preview-card { overflow: hidden; }
.preview-top { display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 30px 30px 23px; border-bottom: 1px solid #edf0eb; }
.preview-top .panel-title { margin-top: 10px; }
.preview-top .panel-intro { margin-top: 5px; }
.download { display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  min-height: 39px; padding: 0 13px; border: 1px solid #c9dfd1; border-radius: 8px;
  background: #eff7f0; color: var(--green-dark); font-size: 12px; font-weight: 730;
  text-decoration: none; white-space: nowrap; }
.download:hover { background: #e1f0e5; }
.preview-blank { min-height: 510px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; padding: 28px 26px 52px; text-align: center; }
.paper-stack { position: relative; width: 158px; height: 191px; margin: 0 0 20px; }
.paper-stack::before, .paper-face { position: absolute; width: 135px; height: 172px;
  border: 1px solid #dce8dc; border-radius: 6px; background: white; }
.paper-stack::before { content: ''; top: 10px; left: 20px; transform: rotate(7deg); background: #eef4eb; }
.paper-face { top: 0; left: 9px; padding: 28px 18px; transform: rotate(-4deg);
  box-shadow: 0 12px 25px rgba(38, 72, 47, .1); }
.paper-face i { display: block; height: 5px; margin-bottom: 11px; border-radius: 5px; background: #dce7dc; }
.paper-face i:first-child { width: 64%; height: 7px; margin-bottom: 21px; background: #6d9c7b; }
.paper-face i:nth-child(3) { width: 82%; }
.paper-face i:nth-child(4) { width: 70%; }
.paper-face i:nth-child(5) { width: 88%; margin-top: 25px; }
.preview-blank h3 { margin: 0; font-size: 17px; letter-spacing: -.03em; }
.preview-blank p { max-width: 300px; margin: 10px 0 0; color: var(--muted);
  font-size: 12px; line-height: 1.8; }
.preview-features { display: flex; justify-content: center; flex-wrap: wrap; gap: 10px;
  margin-top: 25px; }
.preview-features span { padding: 7px 10px; border-radius: 7px; background: #f2f5f1;
  color: #63776a; font-size: 11px; }
.viewer-wrap { padding: 14px; background: #f2f4f1; }
iframe { display: block; width: 100%; height: min(76vh, 830px); min-height: 510px;
  border: 1px solid #d5ddd6; border-radius: 5px; background: white; }
.site-footer { display: flex; justify-content: space-between; align-items: center;
  gap: 20px; padding: 24px 0 39px; border-top: 1px solid var(--line); }
.site-footer small { color: #8b9690; font-size: 11px; }
.quit button { padding: 6px 0; border: 0; background: none; color: var(--muted);
  font-size: 12px; cursor: pointer; }
.quit button:hover { color: var(--ink); text-decoration: underline; }
@media (max-width: 980px) {
  .shell { padding: 0 25px; }
  .workspace { grid-template-columns: 1fr; }
  .preview-blank { min-height: 350px; }
  .hero { padding-top: 53px; }
}
@media (max-width: 600px) {
  .shell { padding: 0 17px; }
  .site-header { min-height: 68px; }
  .brand-sub, .brand-divider, .header-meta > span:first-child { display: none; }
  .hero { display: block; padding: 44px 0 30px; }
  .hero-stat { display: none; }
  h1 { font-size: clamp(32px, 9vw, 42px); }
  .hero p { font-size: 13px; }
  .workspace { gap: 14px; }
  .builder { padding: 23px 19px; }
  .preview-top { padding: 22px 19px; }
  .form-bottom { grid-template-columns: 1fr; }
  .primary { width: 100%; }
  .preview-blank { min-height: 330px; }
  .viewer-wrap { padding: 9px; }
  iframe { min-height: 460px; height: 68vh; }
  .site-footer { align-items: start; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .primary, textarea { transition: none; }
}
"""


def render_page(
    *, questions: str, space: str, error: str, preview: tuple[str, int] | None,
    quit_token: str, first_year: int, last_year: int, paper_count: int,
) -> str:
    options = "".join(
        f'<option value="{value}" {"selected" if value == space else ""}>{label}</option>'
        for value, label in (
            ("compact", "较少留白"), ("standard", "标准留白"), ("spacious", "较多留白"),
        )
    )
    error_html = (
        f'<div class="alert" role="alert">{html.escape(error)}</div>' if error else ""
    )
    if preview is None:
        preview_html = """
        <div class="preview-blank">
          <div class="paper-stack" aria-hidden="true"><div class="paper-face">
            <i></i><i></i><i></i><i></i><i></i>
          </div></div>
          <h3>你的精选卷，从这里开始</h3>
          <p>输入想重做的题目，预览会在这里生成。确认排版后，下载 PDF 即可打印练习。</p>
          <div class="preview-features" aria-label="组卷特点">
            <span>自动按题型整理</span><span>保留原题图文</span><span>解答题留白</span>
          </div>
        </div>"""
        preview_intro = "填好左侧的题目清单，生成后即可查看整张试卷。"
        download_html = ""
    else:
        token, count = preview
        safe_token = html.escape(token, quote=True)
        preview_html = (
            f'<div class="viewer-wrap"><iframe title="试卷 PDF 预览" '
            f'src="/pdf/{safe_token}"></iframe></div>'
        )
        preview_intro = f"已选 {count} 道题，按原题型排序。"
        download_html = (
            f'<a class="download" href="/download/{safe_token}">下载 PDF '
            '<span aria-hidden="true">↗</span></a>'
        )
    year_span = f"{first_year}—{last_year}"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f6f7f4">
  <title>拼好题 · 数学一真题组卷</title>
  <style>{CSS}</style>
</head>
<body>
  <a class="skip-link" href="#workspace">跳转到组卷区域</a>
  <div class="shell">
    <header class="site-header">
      <a class="brand" href="/" aria-label="拼好题首页">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="brand-name">拼好题</span><span class="brand-divider"></span>
        <span class="brand-sub">真题研习</span>
      </a>
      <div class="header-meta"><span>考研数学一</span><span class="status">本地运行</span></div>
    </header>
    <main>
      <section class="hero" aria-labelledby="page-title">
        <div class="hero-copy">
          <div class="eyebrow">YOUR PRACTICE, YOUR PAPER</div>
          <h1 id="page-title">把值得重做的题，<br><span>拼成你的下一套练习。</span></h1>
          <p>从 {year_span} 年考研数学一真题中选题。写下年份和题号，几步就能得到一份适合打印、留有演算空间的复习卷。</p>
        </div>
        <div class="hero-stat" aria-label="题库包含 {paper_count} 份原卷">
          <strong>{paper_count:02d}</strong><small>份真题原卷 · {year_span}</small>
        </div>
      </section>
      <section class="workspace" id="workspace" aria-label="组卷工作台">
        <div class="card builder">
          <div class="panel-kicker">01 / 选题</div>
          <h2 class="panel-title">你的题目清单</h2>
          <p class="panel-intro">按记忆或错题本填写，题目会自动整理进新卷。</p>
          <form method="post" action="/preview">
            <div class="field-header"><label for="questions">年份与题号</label><small>每行一道题</small></div>
            <textarea id="questions" name="questions" aria-describedby="question-help"
              placeholder="2009年数学一第9题&#10;2022-17&#10;2025-22">{html.escape(questions)}</textarea>
            <p class="input-help" id="question-help">支持 <code>2025-22</code> 或“2025年数学一第22题”，重复的题目会自动去重。</p>
            {error_html}
            <div class="form-bottom">
              <div class="select-block"><label for="space">解答题留白</label>
                <select id="space" name="space">{options}</select></div>
              <button class="primary" type="submit">生成试卷预览 <span class="arrow" aria-hidden="true">→</span></button>
            </div>
          </form>
          <div class="local-note"><b aria-hidden="true">✓</b><span>题目与试卷只在这台电脑上处理，无需上传或联网。</span></div>
        </div>
        <section class="card preview-card" id="preview" aria-labelledby="preview-title">
          <div class="preview-top">
            <div><div class="panel-kicker">02 / 预览</div>
              <h2 class="panel-title" id="preview-title">试卷预览</h2>
              <p class="panel-intro">{preview_intro}</p></div>
            {download_html}
          </div>
          {preview_html}
        </section>
      </section>
    </main>
    <footer class="site-footer">
      <small>拼好题 · {year_span} 年考研数学一真题</small>
      <form class="quit" method="post" action="/quit">
        <input type="hidden" name="quit_token" value="{html.escape(quit_token, quote=True)}">
        <button type="submit">结束程序</button>
      </form>
    </footer>
  </div>
</body>
</html>"""
