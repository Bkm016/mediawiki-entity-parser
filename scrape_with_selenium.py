#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Selenium 的 Minecraft Wiki 版本历史爬虫
绕过反爬虫限制
"""

import re
import json

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import time

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


@dataclass
class VersionRecord:
    """版本记录数据类"""
    date: str
    time: str
    editor: str
    file_size: str
    change_bytes: str
    description: str
    wiki_url: str
    edit_url: str


class SeleniumScraper:
    """使用 Selenium 的爬虫"""
    
    def __init__(self):
        self.base_url = "https://minecraft.wiki"
        self.history_url = "https://minecraft.wiki/w/Java_Edition_protocol/Entity_metadata?action=history&limit=500&offset="
        self.driver = None
    
    def setup_driver(self):
        """设置 Chrome 驱动"""
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium 未安装。请运行: pip install selenium")
            print("❌ 还需要下载 ChromeDriver: https://chromedriver.chromium.org/")
            return False
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无界面模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"❌ 无法启动 Chrome 驱动: {e}")
            return False
    
    def has_version_info(self, text: str) -> bool:
        """检查文本中是否包含版本信息"""
        if not text:
            return False
        return "1." in text
    
    def scrape_with_selenium(self) -> List[VersionRecord]:
        """使用 Selenium 爬取"""
        if not self.setup_driver():
            return []
        
        try:
            print(f"🌐 正在访问: {self.history_url}")
            self.driver.get(self.history_url)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            print("✅ 页面加载完成")
            time.sleep(2)  # 额外等待
            
            # 获取页面源码
            page_source = self.driver.page_source
            print(f"📄 页面大小: {len(page_source)} 字符")
            
            # 保存页面源码用于调试
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            print("💾 已保存页面源码到 debug_page_source.html")
            
            return self.parse_selenium_html(page_source)
            
        finally:
            if self.driver:
                self.driver.quit()
    
    def parse_selenium_html(self, html: str) -> List[VersionRecord]:
        """解析 Selenium 获取的历史记录页面 HTML"""
        records = []
        
        print("🔍 开始解析历史记录页面...")
        
        print("🔄 直接解析 data-mw-revid 和基本信息...")
        
        # 直接查找所有包含 oldid 的行
        oldid_lines = re.findall(r'<li[^>]*data-mw-revid="(\d+)"[^>]*>(.*?)</li>', html, re.DOTALL)
        
        print(f"🔍 找到 {len(oldid_lines)} 个修订记录")
        matches = []  # 设置为空，强制使用下面的逻辑
        
        # 处理找到的修订记录
        for oldid, line_content in oldid_lines:
            # 提取时间戳
            time_match = re.search(r'(\d{1,2}:\d{2}), (\d{1,2} \w+ \d{4})', line_content)
            if not time_match:
                continue
                
            time_part, date_part = time_match.groups()
            
            # 提取编辑者
            editor_match = re.search(r'<a[^>]*title="User:([^"]*)"[^>]*><bdi>([^<]*)</bdi></a>', line_content)
            editor = editor_match.group(2) if editor_match else "Unknown"
            
            # 提取文件大小
            size_match = re.search(r'(\d{1,3}(?:,\d{3})*)\s+bytes', line_content)
            file_size = size_match.group(1) if size_match else "Unknown"
            
            # 提取变更
            change_match = re.search(r'([+-]\d+)', line_content)
            change_bytes = change_match.group(1) if change_match else "0"
            
            # 提取注释 (处理嵌套 HTML 标签)
            # 查找 comment span 的开始位置
            comment_start = re.search(r'<span[^>]*class="comment[^"]*"[^>]*>', line_content)
            if comment_start:
                start_pos = comment_start.end()
                # 从开始位置查找匹配的结束标签，考虑嵌套
                span_count = 1
                pos = start_pos
                while pos < len(line_content) and span_count > 0:
                    span_open = line_content.find('<span', pos)
                    span_close = line_content.find('</span>', pos)
                    
                    if span_close == -1:
                        break
                    
                    if span_open != -1 and span_open < span_close:
                        span_count += 1
                        pos = span_open + 5
                    else:
                        span_count -= 1
                        pos = span_close + 7
                        
                if span_count == 0:
                    comment_html = line_content[start_pos:pos-7]  # 减去 </span> 的长度
                    # 移除 HTML 标签，保留文本内容
                    comment = re.sub(r'<[^>]+>', '', comment_html).strip()
                    # 清理多余的空格和特殊字符
                    comment = re.sub(r'\s+', ' ', comment).strip()
                else:
                    comment = ""
            else:
                comment = ""
            
            # 检查是否包含版本信息
            if self.has_version_info(comment):
                wiki_url = f"{self.base_url}/w/Java_Edition_protocol/Entity_metadata?oldid={oldid}"
                edit_url = f"{self.base_url}/w/Java_Edition_protocol/Entity_metadata?action=edit&oldid={oldid}"
                
                record = VersionRecord(
                    date=date_part,
                    time=time_part,
                    editor=editor,
                    file_size=file_size,
                    change_bytes=change_bytes,
                    description=comment,
                    wiki_url=wiki_url,
                    edit_url=edit_url
                )
                records.append(record)
                print(f"✅ 发现版本记录: ({date_part}) - oldid={oldid} - {comment[:50]}...")
            else:
                # 跳过没有版本信息的记录
                if comment:
                    # 特殊记录：如果是可疑的遗漏，显示完整 comment
                    if "entity" in comment.lower() or "metadata" in comment.lower():
                        print(f"⏭️  跳过无版本: oldid={oldid} - FULL: {comment}")
                    else:
                        print(f"⏭️  跳过无版本: oldid={oldid} - {comment[:50]}...")
                else:
                    print(f"⏭️  跳过无评论: oldid={oldid}")
        
        print(f"🎯 解析完成，找到 {len(records)} 条记录")
        return records





def save_results(records: List[VersionRecord]):
    """保存结果到文件"""
    if not records:
        return
    
    # JSON
    with open("minecraft_complete_versions.json", 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)
    
    
    print(f"💾 已保存: minecraft_complete_versions.json")


def parse_saved_page():
    """解析已保存的页面内容"""
    print("🚀 解析已保存的页面内容")
    print("=" * 60)
    
    try:
        with open("debug_page_source.html", "r", encoding="utf-8") as f:
            html = f.read()
        
        print(f"📄 读取页面内容: {len(html):,} 字符")
        
        scraper = SeleniumScraper()
        records = scraper.parse_selenium_html(html)
        
        if records:
            print(f"\n✅ 成功解析 {len(records)} 个版本记录")
            
            # 显示前10个版本
            print("\n📊 发现的版本记录:")
            for i, record in enumerate(records[:10]):
                oldid = record.wiki_url.split('=')[-1]
                comment_preview = record.description[:30] + "..." if len(record.description) > 30 else record.description
                print(f"  {i+1:2d}. {record.date:15} | {record.editor:12} | oldid={oldid} | {comment_preview}")
            
            if len(records) > 10:
                print(f"  ... 还有 {len(records) - 10} 个版本")
            
            save_results(records)
            print(f"\n🎯 完成！共处理 {len(records)} 个 Minecraft 版本")
        else:
            print("❌ 未能解析任何版本数据")
            
    except FileNotFoundError:
        print("❌ 未找到 debug_page_source.html 文件")
        print("请先运行 Selenium 爬虫获取页面内容")

def main():
    """主函数"""
    print("🚀 启动 Minecraft 版本历史爬虫")
    print("=" * 60)
    
    # 检查是否已有保存的页面内容
    import os
    if os.path.exists("debug_page_source.html"):
        print("📄 发现已保存的页面内容，直接解析...")
        parse_saved_page()
        return
    
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium 未安装。请运行: pip install selenium")
        print("❌ 还需要下载 ChromeDriver: https://chromedriver.chromium.org/")
        return
    
    selenium_scraper = SeleniumScraper()
    records = selenium_scraper.scrape_with_selenium()
    
    if records:
        print(f"\n✅ 成功获取 {len(records)} 个版本记录")
        
        # 显示前10个版本
        print("\n📊 发现的版本记录:")
        for i, record in enumerate(records[:10]):
            oldid = record.wiki_url.split('=')[-1]
            comment_preview = record.description[:30] + "..." if len(record.description) > 30 else record.description
            print(f"  {i+1:2d}. {record.date:15} | {record.editor:12} | oldid={oldid} | {comment_preview}")
        
        if len(records) > 10:
            print(f"  ... 还有 {len(records) - 10} 个记录")
        
        save_results(records)
        print(f"\n🎯 完成！共处理 {len(records)} 个 Minecraft 版本")
    else:
        print("❌ 未能获取任何版本数据")


if __name__ == "__main__":
    main()
