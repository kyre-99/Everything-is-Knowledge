#!/usr/bin/env python3
"""
Cookie exporter helper.
Shows how to extract cookies from browser DevTools.

Usage:
    uv run python bin/export_cookies_helper.py
"""

print("""
=== Cookie 导出指南 ===

方法 1: 从浏览器开发者工具复制

1. 在 Chrome 打开小红书并登录: https://www.xiaohongshu.com
2. 按 F12 打开开发者工具
3. 切换到 Application (应用程序) 标签
4. 左侧菜单: Storage > Cookies > https://www.xiaohongshu.com
5. 找到这些关键 cookie:
   - web_session (最重要)
   - a1
   - webId
6. 双击 Value 列，复制值

使用方式:
  uv run python bin/web_fetcher.py "https://www.xiaohongshu.com/discovery/item/XXX" \
      --cookies "web_session=YOUR_VALUE; a1=YOUR_VALUE"

方法 2: 保存到 JSON 文件

创建 cookies.json:
{
  "web_session": "your_value",
  "a1": "your_value",
  "webId": "your_value"
}

使用方式:
  uv run python bin/web_fetcher.py "https://www.xiaohongshu.com/discovery/item/XXX" \
      --cookies-file cookies.json

方法 3: 使用 Claude Code 的 /setup-browser-cookies

在 Claude Code 中运行:
  /setup-browser-cookies

这会打开交互界面选择要导入的 cookie 域名。

=== 其他反爬网站 ===

微博 (weibo.com):
  关键 cookie: SUB, SUBP

知乎 (zhihu.com):
  关键 cookie: z_c0

B站 (bilibili.com):
  关键 cookie: SESSDATA

=== 注意 ===

Cookie 会过期，需要定期更新。
不要分享你的 cookie，它包含登录凭证。
""")