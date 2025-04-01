# MD2PDF - Markdown转PDF转换工具

这是一个用于将Markdown文件转换为高质量PDF的工具，专为学术和技术文档设计，支持中文、SVG图像和LaTeX数学公式。

## 特点

- 支持将Markdown文件转换为PDF
- 自动处理SVG图像并转换为PDF
- 支持中文内容和字体
- 使用XeLaTeX引擎实现高质量排版
- 提取SVG图像中的标题信息
- 支持引用参考文献
- 灵活的命令行接口

## 安装

### 依赖

- Python 3.7+
- Pandoc：用于Markdown到LaTeX的转换
- XeLaTeX：用于生成PDF
- Inkscape：用于将SVG转换为PDF

### 安装步骤

1. 克隆此仓库：

```bash
git clone https://github.com/yourusername/md2pdf.git
cd md2pdf
```

2. 安装Python依赖：

```bash
pip install -r requirements.txt
```

3. 安装Pandoc (如果尚未安装)：
   - 访问 https://pandoc.org/installing.html 获取安装指南

4. 安装XeLaTeX：
   - Linux: `sudo apt-get install texlive-xetex texlive-lang-chinese`
   - macOS: 安装MacTeX (https://tug.org/mactex/)
   - Windows: 安装MiKTeX或TeX Live (https://miktex.org/ 或 https://tug.org/texlive/)

5. 安装Inkscape (用于SVG到PDF的转换)：
   - 访问 https://inkscape.org/release/ 获取安装指南

## 使用方法

### 使用Python脚本

```bash
python md2latex_pandoc.py path/to/your/markdown_file.md
```

这将在与Markdown文件同名的目录中生成LaTeX和PDF文件。

### 使用Shell脚本

```bash
./run_tex.sh path/to/your/latex_file.tex [options]
```

选项:
- `-c, --clean`：编译后清理临时文件
- `-o, --open`：编译成功后打开PDF文件

## 目录结构

- `md2latex_pandoc.py`：主转换脚本
- `run_tex.sh`：LaTeX编译脚本
- `latex_style/`：LaTeX模板和样式文件
- `requirements.txt`：Python依赖

## 示例

1. 将Markdown文件转换为PDF：

```bash
python md2latex_pandoc.py example.md
```

2. 直接编译生成的LaTeX文件：

```bash
./run_tex.sh example/example.tex -o
```

## 许可证

MIT

## 贡献

欢迎提交问题和拉取请求！ 