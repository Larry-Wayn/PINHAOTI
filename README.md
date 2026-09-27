# 拼好题

用 2007—2021 年考研数学一真题组装个人复习卷。程序根据题号索引从本机的原卷 PDF 中裁取题目，生成可打印的 PDF。

## 准备原卷

为避免公开传播真题文件，仓库不包含原卷 PDF。请自行准备有权使用的 2007—2021 年数学一真题 PDF，并放入项目根目录的 `sources/` 文件夹。文件名须与 `data/index.json` 中对应年份的 `pdf` 字段一致。

## macOS 源码版

1. 安装 Python 3。
2. 将原卷 PDF 放入 `sources/`。
3. 双击 **启动拼好题.command**。首次启动会联网安装所需组件。
4. 浏览器打开后，每行输入一道题，例如：
   ```text
   2009年数学一第9题
   2012-17
   2021年数学一第22题
   ```
5. 选择解答题留白，点“预览试卷”，确认后下载 PDF。

也可以在终端中安装 `requirements.txt` 的依赖后运行 `python3 app_entry.py`。点击网页底部“结束程序”即可关闭服务。

## 组卷规则

- 题目按原题型分为选择、填空、解答题，并在新卷中连续编号。
- 选择题保留选项和图形；填空题保留原作答横线；解答题添加可选大小的演算留白。
- 卷末列出原年份和原题号；重复输入同一道题只收录一次。
- 目前只处理题目，不生成答案解析。
- PDF 在本机处理，不会上传。

## macOS 应用构建

在 Apple Silicon Mac 上安装 `requirements-build.txt` 中的依赖，再运行 `./build_mac_app.sh`。签名和公证需另行配置。

## 开发

安装 `requirements-dev.txt` 和 pytest 后运行 `python3 -m pytest`。

主要模块：`pinhaoti/selection.py` 解析题号，`crops.py` 裁取题目，`export.py` 排版 PDF，`web.py` 提供本机网页界面，`ui.py` 实现页面。`data/index.json` 保存题目位置索引。
