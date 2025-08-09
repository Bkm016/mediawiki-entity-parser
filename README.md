# MediaWiki Entity Parser

解析 MediaWiki 格式的实体元数据，转换为结构化 JSON。同时提供 Minecraft Wiki 版本历史爬虫功能。

## 使用方法

### 1. 解析本地文件

```bash
# 将源文件放入 source/ 目录
mkdir source
cp your_file.txt source/1.21.8.txt

# 运行解析器
python main.py
```

### 2. 爬取版本历史

```bash
# 爬取 Minecraft Wiki 版本历史
python scrape_with_selenium.py
```

## 输出文件

### 解析器输出

在 `output/` 目录生成：

- `1.21.8.json` - 结构化数据
- `1.21.8-meanings.txt` - 所有 meaning 字段
- `1.21.8-meaning_to_name.txt` - 转换后的变量名
- `1.21.8-meaning_compare.txt` - 对比文件
- `1.21.8-types.txt` - 所有 type 字段

### 版本历史爬虫输出

- `minecraft_complete_versions.json` - 包含明确版本号的历史记录，每条记录包含版本号、日期、编辑者、修改描述和 oldid URL

## 可选增强

安装 NLP 库以获得更好的变量命名：

```bash
pip install scikit-learn nltk yake keybert
```

安装 Selenium 以使用版本历史爬虫：

```bash
pip install selenium webdriver-manager
```

## 依赖

- Python 3.7+
- selenium（版本历史爬虫）
- webdriver-manager（版本历史爬虫）