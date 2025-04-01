#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
import re
import base64

def extract_and_save_svg(content, output_dir):
    """从Markdown内容中提取SVG代码并保存到文件，并转换为PDF"""
    # 创建保存SVG的目录
    pics_dir = output_dir / 'pics'
    if not pics_dir.exists():
        pics_dir.mkdir(parents=True)
    
    # 定义正则表达式来匹配SVG代码块
    svg_pattern = r'<svg[^>]*>[\s\S]*?</svg>'
    svg_matches = re.finditer(svg_pattern, content)
    
    # 存储SVG文件路径和可能的标题
    svg_files = []
    
    for i, match in enumerate(svg_matches):
        svg_code = match.group(0)
        
        # 尝试从SVG中提取标题信息 - 多种方式
        caption = None
        
        # 1. 尝试从<title>标签提取
        title_match = re.search(r'<title[^>]*>(.*?)</title>', svg_code)
        if title_match:
            caption = title_match.group(1)
            print(f"从<title>标签提取到标题: {caption}")
        
        # 2. 尝试从<text class="title">元素提取
        if not caption:
            # 匹配所有带class="title"属性的text元素及其内容
            text_title_pattern = r'<text[^>]*class="title"[^>]*>(.*?)</text>'
            text_match = re.search(text_title_pattern, svg_code)
            if text_match:
                # 获取带有可能嵌套标签的文本内容
                text_content = text_match.group(1)
                # 处理可能的tspan嵌套标签
                tspan_pattern = r'<tspan[^>]*>(.*?)</tspan>'
                tspans = re.finditer(tspan_pattern, text_content)
                # 替换tspan标签为其内容，保留原始格式
                for tspan in tspans:
                    text_content = text_content.replace(tspan.group(0), tspan.group(1))
                # 清理所有剩余的HTML标签
                clean_text = re.sub(r'<[^>]*>', '', text_content)
                caption = clean_text.strip()
                print(f"从<text class='title'>提取到标题: {caption}")
        
        # 3. 尝试查找SVG代码前面的描述文字作为标题
        if not caption:
            text_before = content[:match.start()].strip()
            desc_match = re.search(r'(?:^|\n)([^\n]*?SVG\s+Visualization[^\n]*?)(?:\n|$)', text_before)
            if desc_match:
                caption = desc_match.group(1).strip()
                print(f"从SVG代码前文本提取到标题: {caption}")
        
        # 4. 尝试从SVG文本内容中提取可能的标题
        if not caption:
            # 搜索所有text元素
            all_texts = re.findall(r'<text[^>]*>(.*?)</text>', svg_code)
            if all_texts and len(all_texts[0]) > 10:  # 假设长度>10的首个文本可能是标题
                caption = re.sub(r'<[^>]*>', '', all_texts[0]).strip()
                print(f"从首个<text>元素提取到可能的标题: {caption}")
        
        # 生成SVG文件名和PDF文件名
        svg_filename = f"figure_{i+1}.svg"
        pdf_filename = f"figure_{i+1}.pdf"
        svg_path = pics_dir / svg_filename
        pdf_path = pics_dir / pdf_filename
        
        # 保存SVG到文件
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg_code)
        
        # 尝试使用inkscape将SVG转换为PDF
        try:
            print(f"尝试将SVG转换为PDF: {svg_filename}")
            convert_cmd = ['inkscape', 
                          str(svg_path), 
                          '--export-filename', str(pdf_path),
                          '--export-area-drawing']
            
            result = subprocess.run(
                convert_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False  # 不立即检查，以便捕获错误
            )
            
            if result.returncode == 0 and pdf_path.exists():
                print(f"成功将SVG转换为PDF: {pdf_filename}")
                # 使用PDF文件路径
                file_to_use = pdf_filename
            else:
                print(f"无法转换SVG到PDF: {result.stderr.decode('utf-8', errors='ignore')}")
                print("将直接使用SVG文件")
                file_to_use = svg_filename
        except Exception as e:
            print(f"转换SVG到PDF时出错: {e}")
            file_to_use = svg_filename
        
        # 添加文件信息
        svg_files.append({
            'path': str(pics_dir.relative_to(output_dir) / file_to_use),
            'caption': caption,
            'index': i+1,
            'placeholder': f"SVG_PLACEHOLDER_{i}",
            'is_pdf': file_to_use.endswith('.pdf')
        })
        
        # 在Markdown内容中替换SVG代码为占位符，方便后续处理
        placeholder_text = f"![图 {i+1}: SVG_PLACEHOLDER_{i}](pics/{file_to_use})"
        content = content.replace(match.group(0), placeholder_text)
    
    return content, svg_files

def convert_md_to_latex(input_file, output_dir, template_path):
    """使用pandoc将Markdown转换为LaTeX"""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"错误: 找不到输入文件 {input_file}")
        return False
    
    # 创建输出目录
    output_dirname = input_path.stem
    output_dir_path = Path(output_dir) / output_dirname if output_dir else input_path.parent / output_dirname
    
    if not output_dir_path.exists():
        output_dir_path.mkdir(parents=True)
    
    # 输出LaTeX文件路径
    tex_file = output_dir_path / f"{input_path.stem}.tex"
    
    # 复制相关资源文件到输出目录
    # 复制模板目录中的样式文件到输出目录
    template_dir = Path(template_path).parent
    for file in template_dir.glob("*.sty"):
        shutil.copy(file, output_dir_path)
    
    # 从Markdown内容中提取图像引用，只复制被引用的图像文件
    # 读取Markdown内容
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取Markdown中引用的图像文件
    img_pattern = r'!\[.*?\]\((.*?)\)'
    img_matches = re.findall(img_pattern, content)
    referenced_images = set()
    for img_path in img_matches:
        # 处理相对路径
        if not os.path.isabs(img_path):
            full_path = input_path.parent / img_path
            if full_path.exists():
                referenced_images.add(full_path)
    
    # 仅复制文档中引用的图像
    for img_path in referenced_images:
        target_path = output_dir_path / img_path.name
        if img_path.exists() and not target_path.exists():
            print(f"复制引用的图像文件: {img_path.name}")
            shutil.copy(img_path, output_dir_path)
    
    # 检查是否有参考文献文件
    input_dir = input_path.parent
    bib_files = list(input_dir.glob('*.bib'))
    if bib_files:
        for bib_file in bib_files:
            # 检查Markdown内容中是否有引用这个bib文件的内容
            bib_referenced = False
            # 简单检查是否有类似@cite的模式
            with open(bib_file, 'r', encoding='utf-8', errors='ignore') as f:
                bib_content = f.read()
                entry_ids = re.findall(r'@\w+\{([^,]+),', bib_content)
                for entry_id in entry_ids:
                    if f"@{entry_id}" in content or f"[@{entry_id}]" in content:
                        bib_referenced = True
                        break
            
            if bib_referenced:
                print(f"复制参考文献文件: {bib_file.name}")
                shutil.copy(bib_file, output_dir_path)
    
    # 提取标题信息
    title = input_path.stem
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1)
    
    # 处理SVG图像
    content, svg_files = extract_and_save_svg(content, output_dir_path)
    
    # 使用pandoc将Markdown转换为LaTeX
    print("使用pandoc转换Markdown到LaTeX...")
    
    # 首先创建一个包含YAML头信息的临时文件
    temp_md_file = output_dir_path / f"{input_path.stem}_temp.md"
    with open(temp_md_file, 'w', encoding='utf-8') as f:
        f.write(f"""---
title: "{title}"
documentclass: ctexart
classoption:
  - a4paper
  - UTF8
header-includes:
  - \\usepackage{{geometry}}
  - \\geometry{{a4paper, margin=1in}}
  - \\usepackage{{graphicx}}
  - \\usepackage{{xcolor}}
  - \\usepackage{{hyperref}}
  - \\usepackage{{fontspec}}
  - \\usepackage{{float}}
---

{content}
""")
    
    # 调用pandoc进行转换
    pandoc_cmd = [
        'pandoc',
        str(temp_md_file),
        '-o', str(tex_file),
        '--pdf-engine=xelatex',
        '-s',
        '--listings'
    ]
    
    if bib_files:
        pandoc_cmd.extend(['--bibliography', str(bib_files[0]), '--citeproc'])
    
    try:
        result = subprocess.run(
            pandoc_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"pandoc成功将Markdown转换为LaTeX")
    except subprocess.CalledProcessError as e:
        print(f"pandoc转换失败: {e}")
        print(f"错误输出: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
    except FileNotFoundError:
        print("找不到pandoc命令，请确保已安装pandoc")
        return False
    finally:
        # 删除临时文件
        if temp_md_file.exists():
            temp_md_file.unlink()
    
    # 对生成的LaTeX文件进行后处理，包括SVG引用处理
    post_process_latex(tex_file, svg_files)
    
    print(f"已生成LaTeX文件: {tex_file}")
    return str(tex_file)

def compile_latex(tex_file):
    """编译LaTeX文件生成PDF"""
    tex_path = Path(tex_file)
    output_dir = tex_path.parent
    tex_filename = tex_path.name
    
    # 切换到输出目录，以便正确处理相对路径
    current_dir = os.getcwd()
    os.chdir(output_dir)
    
    try:
        print("正在编译LaTeX生成PDF...")
        
        # 获取目录中的文件列表
        print("当前目录文件列表:")
        files_before = set(os.listdir('.'))
        for f in sorted(files_before):
            if f.endswith('.pdf'):
                print(f"  {f} - {os.path.getsize(f)} 字节")
        
        # 第一次编译，生成中间文件
        print("第一次编译...")
        subprocess.run(['xelatex', '-interaction=nonstopmode', tex_filename], 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=30, check=False)
        
        # 第二次编译，生成最终PDF
        print("第二次编译...")
        result = subprocess.run(['xelatex', '-interaction=nonstopmode', tex_filename], 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=30, check=False)
        
        # 获取编译后目录文件列表
        files_after = set(os.listdir('.'))
        new_files = files_after - files_before
        
        # 查找生成的PDF文件
        pdf_filename = tex_path.stem + '.pdf'
        pdf_exists = os.path.exists(pdf_filename)
        
        if pdf_exists:
            pdf_size = os.path.getsize(pdf_filename)
            print(f"找到PDF文件: {pdf_filename}, 大小: {pdf_size} 字节")
            if pdf_size > 0:
                print(f"PDF文件已成功生成: {os.path.join(output_dir, pdf_filename)}")
                return True
            else:
                print("PDF文件大小为0，编译可能出现问题")
        else:
            print(f"无法找到PDF文件: {pdf_filename}")
            if new_files:
                print("编译产生的新文件:")
                for f in sorted(new_files):
                    print(f"  {f}")
        
        # 检查日志文件
        log_filename = tex_path.stem + '.log'
        if os.path.exists(log_filename):
            print(f"检查日志文件: {log_filename}")
            with open(log_filename, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
                
                # 检查是否有"output written on"消息
                output_match = re.search(r'Output written on ([^\n]+)', log_content)
                if output_match:
                    print(f"日志中显示已生成输出: {output_match.group(1)}")
                
                # 查找错误信息
                error_lines = [line for line in log_content.split('\n') if '!' in line]
                if error_lines:
                    print("日志中的错误信息:")
                    print('\n'.join(error_lines))
        
        return os.path.exists(pdf_filename) and os.path.getsize(pdf_filename) > 0
    except Exception as e:
        print(f"编译过程中出错: {e}")
        return False
    finally:
        os.chdir(current_dir)

def post_process_latex(tex_file, svg_files=None):
    """后处理LaTeX文件，修复一些特定问题，处理SVG引用"""
    try:
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. 确保文件中包含了正确的字体设置
        if '\\begin{document}' in content and '\\setCJKmainfont' not in content:
            content = content.replace('\\begin{document}', 
                                     '\\setCJKmainfont{STSong}\n'
                                     '\\begin{document}')
            print("已添加CJK字体设置")
        
        # 2. 确保包含必要的包定义
        preamble_additions = []
        
        # 添加所有前言需要的包和命令
        if preamble_additions:
            preamble_text = '\n'.join(preamble_additions) + '\n'
            content = content.replace('\\begin{document}', 
                                     preamble_text + '\\begin{document}')
            print(f"已添加必要的LaTeX包和命令定义")
        
        # 3. 处理图像引用 - 使用更简单的方法
        if svg_files:
            for svg_info in svg_files:
                image_file = svg_info['path'].split('/')[-1]
                fig_caption = svg_info['caption'] if svg_info['caption'] else f"图 {svg_info['index']}"
                
                # 尝试替换caption标签中的占位符内容
                placeholder_caption = f"\\caption{{图 {svg_info['index']}: SVG\\_PLACEHOLDER\\_{svg_info['index']-1}}}"
                real_caption = f"\\caption{{{fig_caption}}}"
                
                if placeholder_caption in content:
                    content = content.replace(placeholder_caption, real_caption)
                    print(f"替换了图像标题: '{placeholder_caption}' -> '{real_caption}'")
                
                # 如果没有找到占位符标题，尝试查找和替换整个figure环境
                if not f"\\caption{{{fig_caption}}}" in content:
                    # 创建图像引用代码
                    figure_code = f"""
\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.8\\textwidth]{{{svg_info['path']}}}
\\caption{{{fig_caption}}}
\\label{{fig:svg_{svg_info['index']}}}
\\end{{figure}}
"""
                    
                    # 尝试各种可能的图像引用模式进行替换
                    patterns_to_check = [
                        f"\\includegraphics{{{svg_info['path']}}}",
                        f"\\includegraphics[width=0.8\\textwidth]{{{svg_info['path']}}}",
                        f"\\includesvg[keepaspectratio]{{{svg_info['path']}}}",
                        f"\\pandocbounded{{\\includesvg[keepaspectratio]{{{svg_info['path']}}}}}",
                    ]
                    
                    replaced = False
                    for pattern in patterns_to_check:
                        if pattern in content:
                            print(f"找到图像引用: {pattern.split('{')[0]}...")
                            if "\\begin{figure}" not in content.split(pattern)[0][-200:]:
                                content = content.replace(pattern, figure_code)
                                replaced = True
                                break
        
        # 4. 修复其他图片的处理
        if '\\includegraphics{' in content:
            content = content.replace('\\includegraphics{', '\\includegraphics[width=0.8\\textwidth]{')
            print("已调整其他图像的宽度")
        
        # 5. 写回文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("已完成LaTeX文件后处理")
        return True
    except Exception as e:
        print(f"后处理LaTeX文件时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())  # 打印详细的错误堆栈
        return False

def main():
    parser = argparse.ArgumentParser(description='将Markdown文件转换为LaTeX并编译成PDF')
    parser.add_argument('markdown_file', help='输入的Markdown文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录路径', default=None)
    parser.add_argument('-t', '--template', help='LaTeX模板文件路径', 
                        default=str(Path('latex_style/template.tex')))
    
    args = parser.parse_args()
    
    # 转换Markdown为LaTeX
    tex_file = convert_md_to_latex(args.markdown_file, args.output_dir, args.template)
    if not tex_file:
        sys.exit(1)
    
    # 后处理LaTeX文件
    post_process_latex(tex_file)
    
    # 编译LaTeX生成PDF
    if not compile_latex(tex_file):
        sys.exit(1)
    
    print("转换和编译完成。")

if __name__ == '__main__':
    main() 