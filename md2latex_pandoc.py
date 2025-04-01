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
        placeholder_text = f"![图 {i+1}: {caption if caption else 'SVG_PLACEHOLDER_'+str(i)}](pics/{file_to_use})"
        content = content.replace(match.group(0), placeholder_text)
    
    return content, svg_files

def find_image_file(md_file_path, img_path):
    """查找图片文件的实际位置"""
    img_file_path = None
    img_file_name = Path(img_path).name
    
    # 递归搜索可能的图片位置
    possible_locations = [
        md_file_path.parent / img_path,                  # 相对于Markdown文件
        Path(img_path),                                  # 当前工作目录
        md_file_path.parent / 'pics' / img_file_name,    # pics子目录
        Path('pics') / img_file_name,                    # 当前工作目录下的pics
    ]
    
    # 添加gemini_paper路径
    if Path('gemini_paper').exists():
        for root, dirs, files in os.walk('gemini_paper'):
            possible_locations.append(Path(root) / img_file_name)
            # 检查pics子目录
            if 'pics' in dirs:
                possible_locations.append(Path(root) / 'pics' / img_file_name)
    
    # 添加所有可能的pics目录
    for root, dirs, files in os.walk('.'):
        if 'pics' in dirs:
            possible_locations.append(Path(root) / 'pics' / img_file_name)
    
    debug_print(f"查找图片 '{img_file_name}' 的可能位置:")
    # 检查所有可能的位置
    for loc in possible_locations:
        debug_print(f"  检查: {loc}")
        if loc.exists():
            img_file_path = loc
            debug_print(f"  找到图像文件: {img_file_path}")
            break
    
    if not img_file_path:
        debug_print(f"  未找到图像文件: {img_file_name}")
    
    return img_file_path

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
    
    # 确保pics目录存在
    pics_dir = output_dir_path / 'pics'
    if not pics_dir.exists():
        pics_dir.mkdir(parents=True)
    
    # 输出LaTeX文件路径
    tex_file = output_dir_path / f"{input_path.stem}.tex"
    
    # 复制相关资源文件到输出目录
    # 复制模板目录中的样式文件到输出目录
    template_dir = Path(template_path).parent
    for file in template_dir.glob("*.sty"):
        shutil.copy(file, output_dir_path)
    
    # 从Markdown内容中提取图像引用，复制图像文件
    # 读取Markdown内容
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 打印调试信息 - 展示处理前的Markdown内容
    debug_print(f"\n调试: 原始Markdown内容中的图片引用:")
    # 提取Markdown中引用的图像文件 - 改进正则表达式匹配多种格式
    standard_img_pattern = r'!\[(.*?)\]\((.*?)\)'
    special_img_pattern = r'!\((图\s+\d+:.*?)\)\((.*?)\)'
    
    debug_print("标准图片格式引用:")
    for alt_text, img_path in re.findall(standard_img_pattern, content):
        debug_print(f"  标题: '{alt_text}', 路径: '{img_path}'")
    
    debug_print("特殊图片格式引用:")
    for caption, img_path in re.findall(special_img_pattern, content):
        debug_print(f"  标题: '{caption}', 路径: '{img_path}'")
    
    # 处理所有可能的图片引用模式
    referenced_images = []
    
    # 处理标准图片引用： ![alt](path)
    for alt_text, img_path in re.findall(standard_img_pattern, content):
        img_file_path = find_image_file(input_path, img_path)
        
        if img_file_path:
            img_file_name = Path(img_file_path).name
            target_path = pics_dir / img_file_name
            
            # 复制图片到输出目录
            if not target_path.exists():
                debug_print(f"复制图像文件: {img_file_path} 到 {target_path}")
                shutil.copy(img_file_path, target_path)
            
            # 更新Markdown中的图片引用 - 确保使用正确的相对路径
            new_path = f"pics/{img_file_name}"
            old_ref = f"![{alt_text}]({img_path})"
            new_ref = f"![{alt_text}]({new_path})"
            content = content.replace(old_ref, new_ref)
            
            referenced_images.append((alt_text, target_path, img_file_name))
            debug_print(f"处理标准图片引用: '{alt_text}' -> {new_path}")
        else:
            debug_print(f"警告: 无法找到图像文件: {img_path}")
    
    # 处理特殊图片引用： !(caption)(path)
    for caption, img_path in re.findall(special_img_pattern, content):
        img_file_path = find_image_file(input_path, img_path)
        
        if img_file_path:
            img_file_name = Path(img_file_path).name
            target_path = pics_dir / img_file_name
            
            # 复制图片到输出目录
            if not target_path.exists():
                debug_print(f"复制图像文件: {img_file_path} 到 {target_path}")
                shutil.copy(img_file_path, target_path)
            
            # 更新Markdown中的图片引用 - 特殊格式
            new_path = f"pics/{img_file_name}"
            old_ref = f"!({caption})({img_path})"
            # 直接创建LaTeX图片环境
            fig_num = re.search(r'图\s+(\d+)', caption).group(1) if re.search(r'图\s+(\d+)', caption) else "1"
            new_ref = f"""
\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.8\\textwidth]{{{new_path}}}
\\caption{{{caption}}}
\\label{{fig:figure_{fig_num}}}
\\end{{figure}}
"""
            content = content.replace(old_ref, new_ref)
            
            referenced_images.append((caption, target_path, img_file_name))
            debug_print(f"处理特殊图片引用: '{caption}' -> LaTeX图片环境")
        else:
            debug_print(f"警告: 无法找到图像文件: {img_path}")
    
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

def compile_latex(tex_file, fix_images=False):
    """编译LaTeX文件生成PDF"""
    try:
        # 确保输入文件存在
        tex_path = Path(tex_file)
        if not tex_path.exists():
            print(f"错误: LaTeX文件不存在: {tex_file}")
            return False, None
        
        # LaTeX文件所在目录
        tex_dir = tex_path.parent
        tex_filename = tex_path.name
        pdf_filename = tex_path.stem + '.pdf'
        pdf_file = tex_dir / pdf_filename
        
        # 先移除可能存在的旧PDF，避免误判
        if pdf_file.exists():
            os.remove(pdf_file)
        
        # 获取初始目录文件列表
        initial_files = os.listdir(tex_dir)
        debug_print("正在编译LaTeX生成PDF...")
        
        # 进入LaTeX文件所在目录
        current_dir = os.getcwd()
        os.chdir(tex_dir)
        
        try:
            # 第一次编译: xelatex
            debug_print("第一次编译...")
            xelatex_cmd = ['xelatex', '-interaction=nonstopmode', tex_filename]
            xelatex_result = subprocess.run(
                xelatex_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True  # 使用文本模式
            )
            
            # 第二次编译: xelatex
            debug_print("第二次编译...")
            xelatex_result = subprocess.run(
                xelatex_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 检查编译结果和PDF文件
            pdf_success = os.path.exists(pdf_filename)
            
            # 检查PDF大小
            pdf_size = 0
            if pdf_success:
                pdf_size = os.path.getsize(pdf_filename)
                debug_print(f"找到PDF文件: {pdf_filename}, 大小: {pdf_size} 字节")
            
            # 检查是否真正成功（PDF存在且不为空）
            if pdf_success and pdf_size > 0:
                pdf_path = tex_dir / pdf_filename
                debug_print(f"PDF文件已成功生成: {pdf_path}")
            else:
                # 可能有错误，检查LaTeX日志
                if os.path.exists(f"{tex_path.stem}.log"):
                    with open(f"{tex_path.stem}.log", 'r', encoding='utf-8', errors='ignore') as log_file:
                        log_content = log_file.read()
                        error_lines = [line for line in log_content.split('\n') if '! ' in line]
                        if error_lines:
                            print("编译时遇到错误:")
                            for line in error_lines[:5]:  # 只显示前5个错误
                                print(f"  {line}")
                        else:
                            print("编译过程可能有未知错误，请检查日志文件")
                
                # 检查编译过程的标准输出
                if xelatex_result.returncode != 0:
                    print(f"xelatex返回错误码: {xelatex_result.returncode}")
                    error_output = xelatex_result.stderr
                    if error_output:
                        print("错误输出:", error_output[:500])  # 限制输出长度
                
                return False, None
        
            # 列出目录中的当前文件
            current_files = os.listdir(".")
            debug_print("当前目录文件列表:")
            for f in current_files:
                if f.endswith(".pdf"):
                    debug_print(f"  {f} - {os.path.getsize(f)} 字节")
            
            # 检查图片文件
            pics_dir = Path("pics")
            if pics_dir.exists():
                debug_print("检查图片文件:")
                for img_file in pics_dir.glob("*.*"):
                    debug_print(f"  {img_file.name} - {img_file.stat().st_size} 字节")
            
            # 强化图片修复模式
            if fix_images and pdf_success:
                try:
                    debug_print("使用强化图片修复模式...")
                    
                    # 读取LaTeX文件内容
                    with open(tex_filename, 'r', encoding='utf-8') as f:
                        tex_content = f.read()
                    
                    # 找出所有图片引用
                    img_refs = re.findall(r'\\includegraphics(?:\[.*?\])?\{(.*?)\}', tex_content)
                    debug_print(f"发现 {len(img_refs)} 个图片引用")
                    
                    # 创建一个新版本的LaTeX内容，确保图片引用正确
                    new_tex_content = tex_content
                    
                    # 如果是进一步强化模式，可以在这里添加额外的处理
                    # 例如，确保图片路径正确
                    for img_ref in img_refs:
                        # 检查图片是否存在
                        img_path = Path(img_ref)
                        if not (img_path.is_absolute() or img_path.exists()):
                            # 如果是相对路径且不存在，尝试查找
                            img_name = img_path.name
                            # 搜索可能的位置
                            for root, dirs, files in os.walk('.'):
                                if img_name in files:
                                    found_path = Path(root) / img_name
                                    rel_path = str(found_path.relative_to(".")).replace("\\", "/")
                                    debug_print(f"替换图片路径: {img_ref} -> {rel_path}")
                                    new_tex_content = new_tex_content.replace(f"{{{img_ref}}}", f"{{{rel_path}}}")
                                    break
                    
                    # 只有当内容发生变化时才重写文件和重新编译
                    if new_tex_content != tex_content:
                        debug_print("LaTeX内容已更新，重新编译...")
                        with open(tex_filename, 'w', encoding='utf-8') as f:
                            f.write(new_tex_content)
                        
                        # 重新编译两次
                        debug_print("第一次编译...")
                        subprocess.run(xelatex_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        debug_print("第二次编译...")
                        subprocess.run(xelatex_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        # 再次检查PDF
                        pdf_success = os.path.exists(pdf_filename)
                        if pdf_success:
                            pdf_size = os.path.getsize(pdf_filename)
                            debug_print(f"找到PDF文件: {pdf_filename}, 大小: {pdf_size} 字节")
                        
                            if not (pdf_success and pdf_size > 0):
                                print("强化修复后编译失败，请检查LaTeX错误")
                                return False, None
                
                except Exception as e:
                    print(f"强化图片修复模式出错: {e}")
                    # 继续使用原始编译结果
            
            return True, tex_dir / pdf_filename
        
        finally:
            # 确保返回原始目录
            os.chdir(current_dir)
    
    except Exception as e:
        print(f"编译LaTeX时出错: {e}")
        return False, None

def remove_lstlisting_wrappers(content):
    """
    删除lstlisting环境的包装，保留内部的图片引用代码
    """
    # 查找被lstlisting环境包装的图片引用代码
    pattern = r'\\begin\{lstlisting\}(\[language=XML\])?\s*(\\begin\{figure\}.*?\\end\{figure\})\s*\\end\{lstlisting\}'
    
    # 查找匹配项并替换
    matches = list(re.finditer(pattern, content, re.DOTALL))
    if matches:
        debug_print(f"找到了{len(matches)}处被lstlisting包装的图片引用")
        for match in matches:
            # 提取图片引用代码
            figure_code = match.group(2).strip()
            # 替换整个匹配为仅保留的图片引用代码
            content = content.replace(match.group(0), figure_code)
            debug_print("已移除lstlisting包装，保留图片引用代码")
    
    # 查找并移除空的lstlisting环境
    empty_pattern = r'\\begin\{lstlisting\}(\[language=XML\])?\s*\\end\{lstlisting\}'
    content = re.sub(empty_pattern, '', content)
    
    # 需要单独处理"以下 SVG 图展示..."后面接着的lstlisting环境
    svg_intro_pattern = r'(以下 SVG 图展示[^\n]*)\s*\\begin\{lstlisting\}(\[language=XML\])?\s*(.*?)\\end\{lstlisting\}'
    
    for match in re.finditer(svg_intro_pattern, content, re.DOTALL):
        intro_text = match.group(1)
        listing_content = match.group(3).strip()
        
        # 检查listing内容是否为空或只有图片引用
        if not listing_content or listing_content.isspace():
            # lstlisting为空，检查后面是否有figure环境
            after_listing = content[match.end():].strip()
            figure_pattern = r'\\begin\{figure\}.*?\\end\{figure\}'
            figure_match = re.search(figure_pattern, after_listing, re.DOTALL)
            
            if figure_match:
                # 找到了紧随其后的figure环境，保留intro和figure
                replacement = f"{intro_text}\n\n{figure_match.group(0)}"
                # 替换原文本（包括intro、lstlisting和figure）
                original = content[match.start():match.end() + figure_match.end()]
                content = content.replace(original, replacement)
                debug_print("已处理SVG介绍后的lstlisting并保留图片")
            else:
                # 没有找到紧随其后的figure，尝试在pics目录查找合适的图片
                figure_num = 1  # 默认图片编号
                section_match = re.search(r'\\subsection\{(\d+)', content[:match.start()])
                if section_match:
                    try:
                        section_num = section_match.group(1)
                        figure_num = int(section_num)
                    except ValueError:
                        pass
                
                # 创建新的图片引用
                replacement = f"""{intro_text}

\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.8\\textwidth]{{pics/figure_{figure_num}.pdf}}
\\caption{{研究脉络图}}
\\label{{fig:figure_{figure_num}}}
\\end{{figure}}
"""
                content = content.replace(match.group(0), replacement)
                debug_print(f"已替换空lstlisting为默认图片figure_{figure_num}.pdf")
        elif '\\begin{figure}' in listing_content and '\\end{figure}' in listing_content:
            # lstlisting中包含图片引用，直接提取
            figure_pattern = r'\\begin\{figure\}.*?\\end\{figure\}'
            figure_match = re.search(figure_pattern, listing_content, re.DOTALL)
            if figure_match:
                replacement = f"{intro_text}\n\n{figure_match.group(0)}"
                content = content.replace(match.group(0), replacement)
                debug_print("已从lstlisting中提取并保留图片引用")
    
    return content

def post_process_latex(tex_file, svg_files=None):
    """后处理LaTeX文件，修复一些特定问题，处理SVG引用"""
    try:
        debug_print(f"\n调试: 对LaTeX文件进行后处理: {tex_file}")
        with open(tex_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. 确保文件中包含了正确的字体设置
        if '\\begin{document}' in content and '\\setCJKmainfont' not in content:
            content = content.replace('\\begin{document}', 
                                    '\\setCJKmainfont{STSong}\n'
                                    '\\begin{document}')
            debug_print("已添加CJK字体设置")
            
        # 新增：移除lstlisting环境包装，保留图片引用代码
        content = remove_lstlisting_wrappers(content)
        
        # 2. 确保包含必要的包定义
        preamble_additions = []
        
        # 添加对特殊字符的支持（希腊字母、数学符号等）- 使用更简单的方式
        if "\\usepackage{unicode-math}" in content:
            # 移除可能导致问题的unicode-math包
            content = content.replace("\\usepackage{unicode-math}", "")
            
            # 添加基本的amsmath和amssymb包用于数学符号支持
            if "\\usepackage{amsmath}" not in content:
                preamble_additions.append("\\usepackage{amsmath}")
            if "\\usepackage{amssymb}" not in content:
                preamble_additions.append("\\usepackage{amssymb}")
                
            # 添加直接的希腊字母命令定义
            preamble_additions.append("""
% 定义希腊字母和特殊符号的简单命令
\\newcommand{\\betasym}{$\\beta$}
\\newcommand{\\gammasym}{$\\gamma$}
\\newcommand{\\deltasym}{$\\delta$}
\\newcommand{\\tausym}{$\\tau$}
\\newcommand{\\doublearrow}{$\\leftrightarrow$}
\\newcommand{\\doublelarrow}{$\\Leftrightarrow$}
""")
            debug_print("已添加特殊字符支持（简化版本）")
        
        # 添加所有前言需要的包和命令
        if preamble_additions:
            preamble_text = '\n'.join(preamble_additions) + '\n'
            # 找一个合适的位置插入这些定义
            if "\\usepackage{amsmath}" in content:
                content = content.replace("\\usepackage{amsmath}", "\\usepackage{amsmath}\n" + preamble_text)
            else:
                content = content.replace('\\begin{document}', preamble_text + '\\begin{document}')
            debug_print(f"已添加必要的LaTeX包和命令定义")
        
        # 3. 替换文本中的特殊字符为TeX命令
        # 希腊字母替换 - 使用更简单的方式
        greek_chars = {
            "β": "\\betasym{}",
            "γ": "\\gammasym{}",
            "δ": "\\deltasym{}",
            "τ": "\\tausym{}",
            "↔": "\\doublearrow{}",
            "⟺": "\\doublelarrow{}"
        }
        
        # 在普通文本中替换特殊字符（但避免替换命令定义等区域）
        for char, command in greek_chars.items():
            if char in content:
                # 使用更安全的替换方法
                parts = content.split(char)
                new_content = parts[0]
                for i in range(1, len(parts)):
                    # 检查前一个字符，避免替换已有的命令
                    if new_content and new_content[-1] not in '\\{':
                        new_content += command
                    else:
                        new_content += char
                    new_content += parts[i]
                content = new_content
        
        debug_print("已处理特殊字符")
        
        # 4. 处理SVG图像引用
        if svg_files:
            for svg_info in svg_files:
                image_file = svg_info['path'].split('/')[-1]
                fig_caption = svg_info['caption'] if svg_info['caption'] else f"图 {svg_info['index']}"
                
                # 修复图像引用问题 - 查找各种可能的引用模式
                placeholder_patterns = [
                    f"图 {svg_info['index']}: SVG_PLACEHOLDER_{svg_info['index']-1}",
                    f"SVG_PLACEHOLDER_{svg_info['index']-1}",
                    f"图 {svg_info['index']}:"
                ]
                
                # 查找图像引用并修复
                for pattern in placeholder_patterns:
                    # 检查是否有caption包含这个占位符
                    caption_pattern = f"\\caption{{{pattern}}}"
                    if caption_pattern in content:
                        content = content.replace(caption_pattern, f"\\caption{{{fig_caption}}}")
                        debug_print(f"替换了图像标题: '{pattern}' -> '{fig_caption}'")
                        break
                
                # 查找缺失的图像引用并修复
                svg_path = svg_info['path']
                if f"\\includegraphics{{{svg_path}}}" not in content and \
                   f"\\includegraphics[width=0.8\\textwidth]{{{svg_path}}}" not in content:
                    
                    # 检查是否存在不完整的图像引用
                    image_name = svg_path.split('/')[-1]
                    if f"\\includegraphics{{{image_name}}}" in content:
                        # 修复相对路径问题
                        content = content.replace(
                            f"\\includegraphics{{{image_name}}}", 
                            f"\\includegraphics[width=0.8\\textwidth]{{{svg_path}}}"
                        )
                        debug_print(f"修复了图像路径: '{image_name}' -> '{svg_path}'")
                    elif "SVG_PLACEHOLDER" in content:
                        # 查找包含占位符的段落，并添加正确的图像引用
                        for placeholder in placeholder_patterns:
                            if placeholder in content:
                                paragraph_with_placeholder = re.search(
                                    f"[^\n]*{re.escape(placeholder)}[^\n]*", 
                                    content
                                )
                                if paragraph_with_placeholder:
                                    # 创建图像代码
                                    figure_code = f"""
\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.8\\textwidth]{{{svg_path}}}
\\caption{{{fig_caption}}}
\\label{{fig:svg_{svg_info['index']}}}
\\end{{figure}}
"""
                                    # 替换包含占位符的段落
                                    content = content.replace(
                                        paragraph_with_placeholder.group(0),
                                        figure_code
                                    )
                                    debug_print(f"添加了图像引用: 图 {svg_info['index']}")
                                    break
        
        # 5. 强化图片处理 - 确保在LaTeX中正确加载图片
        img_packages = [
            "\\usepackage{graphicx}",  # 基本图形包
            "\\usepackage{float}"      # 用于控制图片位置
        ]
        
        # 确保需要的包都被加载
        for pkg in img_packages:
            if pkg not in content:
                content = content.replace('\\documentclass', f'{pkg}\n\\documentclass')
        
        # 确保图片路径正确 - 移除路径中的多余空格
        img_pattern = r'\\includegraphics(\[.*?\])?\{\s*(.*?)\s*\}'
        for match in re.finditer(img_pattern, content):
            old_tag = match.group(0)
            options = match.group(1) or ''
            path = match.group(2).strip()  # 移除路径两端的空格
            
            # 构建新的图片标签，确保格式正确
            new_tag = f'\\includegraphics{options}{{{path}}}'
            if old_tag != new_tag:
                content = content.replace(old_tag, new_tag)
                debug_print(f"修复图片路径格式: {old_tag} -> {new_tag}")
        
        # 6. 修复图像路径问题（特别是未指定pics/目录的图片）
        img_pattern = r'\\includegraphics(\[.*?\])?{((?!pics/).+?\.(?:pdf|png|jpg|jpeg))}'
        for match in re.finditer(img_pattern, content):
            options = match.group(1) or ''
            img_path = match.group(2)
            if not img_path.startswith('pics/') and not img_path.startswith('/'):
                fixed_path = f"pics/{img_path}"
                content = content.replace(
                    f"\\includegraphics{options}{{{img_path}}}", 
                    f"\\includegraphics[width=0.8\\textwidth]{{{fixed_path}}}"
                )
                debug_print(f"修复了图像路径: '{img_path}' -> '{fixed_path}'")
                
                # 检查图片文件是否存在，不存在则尝试查找并复制
                output_dir = Path(tex_file).parent
                target_path = output_dir / fixed_path
                if not target_path.exists():
                    img_name = Path(img_path).name
                    found = False
                    
                    # 递归查找图片
                    for root, dirs, files in os.walk('.'):
                        if img_name in files:
                            source_path = Path(root) / img_name
                            os.makedirs(target_path.parent, exist_ok=True)
                            debug_print(f"找到并复制图片: {source_path} -> {target_path}")
                            shutil.copy(source_path, target_path)
                            found = True
                            break
                    
                    if not found:
                        debug_print(f"警告: 无法找到图片文件 {img_name} 以复制到 {target_path}")
        
        # 7. 确保所有图片引用都被包装在figure环境中
        img_refs = re.findall(r'\\includegraphics(?:\[.*?\])?\{(pics/[^}]+)\}', content)
        for img_ref in img_refs:
            # 检查这个引用是否已经在figure环境中
            img_pattern = f'\\\\includegraphics(?:\\[.*?\\])?\\{{{re.escape(img_ref)}\\}}'
            
            # 查找匹配的includegraphics标签
            match = re.search(img_pattern, content)
            if match:
                # 检查前后文是否已有figure环境
                before_ctx = content[:match.start()].rfind('\\begin{figure')
                after_ctx = content[match.end():].find('\\end{figure}')
                
                # 如果没有在figure环境中
                if before_ctx == -1 or content[before_ctx:match.start()].find('\\end{figure}') != -1 or after_ctx == -1:
                    # 提取文件名和编号
                    file_name = Path(img_ref).name
                    fig_num = "1"
                    if "figure_" in file_name:
                        fig_num_match = re.search(r'figure_(\d+)', file_name)
                        if fig_num_match:
                            fig_num = fig_num_match.group(1)
                    
                    # 创建完整的figure环境
                    img_tag = match.group(0)
                    figure_env = f"""
\\begin{{figure}}[H]  % H强制图片在当前位置
\\centering
{img_tag}
\\caption{{图 {fig_num}}}
\\label{{fig:figure_{fig_num}}}
\\end{{figure}}
"""
                    # 替换原始图片标签
                    content = content.replace(img_tag, figure_env)
                    debug_print(f"为图片添加figure环境: {img_ref}")
        
        # 8. 处理特殊的图片引用格式
        # 8.1 处理 !(图 6: 普适性标度律示意图)(pics/figure_6.pdf) 格式
        special_img_pattern = r'!\((图\s+\d+:.+?)\)\((pics/figure_\d+\.pdf)\)'
        for match in re.finditer(special_img_pattern, content):
            caption = match.group(1)
            img_path = match.group(2)
            
            # 获取图片编号
            fig_num = re.search(r'图\s+(\d+)', caption).group(1)
            
            # 创建正确的figure环境
            figure_code = f"""
\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.8\\textwidth]{{{img_path}}}
\\caption{{{caption}}}
\\label{{fig:figure_{fig_num}}}
\\end{{figure}}
"""
            # 替换原始的引用
            content = content.replace(match.group(0), figure_code)
            debug_print(f"修复了特殊图片引用: {caption}")
        
        # 8.2 修复已有的未正确处理的图片引用
        # 查找类似 ! [ 图 6: 普适性标度律示意图 ] ( pics/figure_6.pdf ) 的模式
        existing_img_pattern = r'!\s*\[\s*(图\s+\d+:.*?)\s*\]\s*\(\s*(pics/figure_\d+\.pdf)\s*\)'
        for match in re.finditer(existing_img_pattern, content):
            caption = match.group(1)
            img_path = match.group(2)
            
            # 获取图片编号
            fig_num_match = re.search(r'图\s+(\d+)', caption)
            if fig_num_match:
                fig_num = fig_num_match.group(1)
                
                # 检查是否已经在figure环境中
                if "\\begin{figure}" not in content.split(match.group(0))[0][-200:]:
                    # 创建figure环境
                    figure_code = f"""
\\begin{{figure}}[htbp]
\\centering
\\includegraphics[width=0.8\\textwidth]{{{img_path}}}
\\caption{{{caption}}}
\\label{{fig:figure_{fig_num}}}
\\end{{figure}}
"""
                    # 替换原始引用
                    content = content.replace(match.group(0), figure_code)
                    debug_print(f"修复了标准图片引用: {caption}")
        
        # 9. 处理可能在文本中直接出现的LaTeX图片代码 (防止被当作文本显示)
        # 9.1 处理转义的LaTeX代码
        text_latex_pattern = r'\\\\begin\{figure\}.*?\\\\end\{figure\}'
        for match in re.finditer(text_latex_pattern, content, re.DOTALL):
            escaped_code = match.group(0)
            # 将双反斜杠替换为单反斜杠
            fixed_code = escaped_code.replace('\\\\', '\\')
            content = content.replace(escaped_code, fixed_code)
            debug_print(f"修复了转义的LaTeX代码")
        
        # 9.2 处理图形环境中的空行，确保LaTeX正确处理
        figure_blocks = re.findall(r'\\begin{figure}.*?\\end{figure}', content, re.DOTALL)
        for block in figure_blocks:
            # 删除多余的空行，但保留基本结构
            fixed_block = re.sub(r'\n\s*\n', '\n', block)
            if block != fixed_block:
                content = content.replace(block, fixed_block)
                debug_print("修复了figure环境中的空行")
        
        # 10. 在preamble中添加额外的图片支持
        if '\\begin{document}' in content:
            preamble_additions = """
% 增强图片处理支持
\\usepackage{graphicx}
\\usepackage{float}
\\DeclareGraphicsExtensions{.pdf,.png,.jpg}
\\graphicspath{{./pics/}}  % 指定图片搜索路径

% 定义图片样式
\\renewcommand{\\figurename}{图}
"""
            # 检查是否已经有这些设置
            if '\\graphicspath' not in content:
                # 在文档开始前添加这些设置
                content = content.replace('\\begin{document}', preamble_additions + '\\begin{document}')
                debug_print("添加了图片处理增强设置")
        
        # 11. 确保图片文件存在
        tex_dir = Path(tex_file).parent
        pics_dir = tex_dir / 'pics'
        if not pics_dir.exists():
            pics_dir.mkdir(parents=True)
            debug_print(f"创建图片目录: {pics_dir}")
        
        for img_ref in img_refs:
            img_path = tex_dir / img_ref
            if not img_path.exists():
                debug_print(f"警告: 图片文件不存在 {img_path}")
                # 搜索整个项目查找同名图片
                img_name = img_path.name
                for root, dirs, files in os.walk('.'):
                    for file in files:
                        if file == img_name:
                            source = Path(root) / file
                            debug_print(f"找到替代图片: {source}")
                            # 确保目标目录存在
                            img_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy(source, img_path)
                            debug_print(f"已复制图片: {source} -> {img_path}")
                            break
                    if img_path.exists():
                        break
        
        # 添加调试输出 - 列出所有图片引用和状态
        debug_print(f"\n调试: LaTeX内容中的图片引用:")
        for img_ref in img_refs:
            img_path = tex_dir / img_ref
            debug_print(f"  图片引用: {img_ref}")
            debug_print(f"  文件存在: {img_path.exists()}, 大小: {img_path.stat().st_size if img_path.exists() else 0} 字节")
        
        # 写回文件
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        debug_print("已完成LaTeX文件后处理")
        return True
    except Exception as e:
        print(f"后处理LaTeX文件时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())  # 打印详细的错误堆栈
        return False

def main():
    """处理主程序逻辑"""
    parser = argparse.ArgumentParser(
        description='将Markdown文件转换为LaTeX并编译成PDF - 支持中文、数学公式和图片',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  简单转换:
    python md2latex_pandoc.py ./example.md
  
  自动打开PDF:
    python md2latex_pandoc.py ./example.md --open
    
  指定输出目录:
    python md2latex_pandoc.py ./example.md -o ./output_dir
    
  使用自定义模板:
    python md2latex_pandoc.py ./example.md -t ./my_template.tex
"""
    )
    parser.add_argument('markdown_file', help='输入的Markdown文件路径')
    parser.add_argument('-o', '--output-dir', help='输出目录路径 (默认为Markdown文件所在目录)', default=None)
    parser.add_argument('-t', '--template', help='LaTeX模板文件路径 (默认使用内置模板)', 
                        default=str(Path('latex_style/template.tex')))
    parser.add_argument('--open', action='store_true', help='编译完成后自动打开PDF文件')
    parser.add_argument('--fix-images', action='store_true', help='使用更强的图片修复模式，尝试解决图片不显示问题')
    parser.add_argument('--quiet', action='store_true', help='减少输出信息，仅显示必要信息')
    
    args = parser.parse_args()
    
    # 设置全局输出模式
    global VERBOSE
    VERBOSE = not args.quiet
    
    if VERBOSE:
        print(f"处理Markdown文件: {args.markdown_file}")
        if args.output_dir:
            print(f"输出目录: {args.output_dir}")
        if args.open:
            print("编译完成后将自动打开PDF文件")
    else:
        print(f"处理文件: {args.markdown_file}")
    
    # 转换Markdown为LaTeX
    tex_file = convert_md_to_latex(args.markdown_file, args.output_dir, args.template)
    if not tex_file:
        print("转换失败，请检查错误信息")
        sys.exit(1)
    
    # 后处理LaTeX文件
    post_process_latex(tex_file)
    
    # 编译LaTeX生成PDF
    success, pdf_path = compile_latex(tex_file, args.fix_images)
    if not success:
        print("编译失败，请检查LaTeX错误")
        sys.exit(1)
    
    print("转换和编译完成。")
    
    # 如果指定了--open选项，则自动打开PDF
    if args.open and pdf_path and os.path.exists(pdf_path):
        try:
            print(f"正在打开PDF文件: {pdf_path}")
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', pdf_path], check=True)
            elif sys.platform == 'win32':  # Windows
                os.startfile(pdf_path)
            else:  # Linux or other Unix
                subprocess.run(['xdg-open', pdf_path], check=True)
        except Exception as e:
            print(f"尝试打开PDF时出错: {e}")
            print("请手动打开PDF文件: " + pdf_path)

# 添加全局变量控制详细输出
VERBOSE = True

def debug_print(*args, **kwargs):
    """只在非静默模式下打印调试信息"""
    if VERBOSE:
        print(*args, **kwargs)

def extract_titles_and_images(md_file):
    """从Markdown中提取标题和图像，为后续处理做准备"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            global DOCUMENT_TITLE
            DOCUMENT_TITLE = title_match.group(1).strip()
            debug_print(f"提取到文档标题: {DOCUMENT_TITLE}")
        
        # 调试输出Markdown中的图片引用
        debug_print("\n调试: 原始Markdown内容中的图片引用:")
        
        # 查找标准图片格式 ![alt](path)
        standard_img_refs = re.findall(r'!\[(.*?)\]\((.*?)\)', content)
        debug_print("标准图片格式引用:")
        for alt, path in standard_img_refs:
            debug_print(f"  {alt}: {path}")
        
        # 查找特殊格式 !(alt)(path)
        special_img_refs = re.findall(r'!\((.*?)\)\((.*?)\)', content)
        debug_print("特殊图片格式引用:")
        for alt, path in special_img_refs:
            debug_print(f"  {alt}: {path}")
        
        # 处理SVG图像：查找SVG代码块并转换为PDF
        svg_pattern = r'```xml\s*<svg.*?</svg>\s*```'
        svg_blocks = re.findall(svg_pattern, content, re.DOTALL)
        
        global SVG_FILES
        SVG_FILES = []
        
        for i, svg_block in enumerate(svg_blocks):
            # 从SVG代码中提取<title>标签内容作为图片标题
            title_match = re.search(r'<title>(.*?)</title>', svg_block)
            title = f"SVG图{i+1}" if not title_match else title_match.group(1)
            debug_print(f"从<title>标签提取到标题: {title}")
            
            # 清理SVG代码，去除```xml和```
            svg_code = re.sub(r'```xml\s*|\s*```$', '', svg_block)
            
            # 生成文件名
            output_dir = os.path.dirname(md_file)
            if not os.path.exists(f"{output_dir}/pics"):
                os.makedirs(f"{output_dir}/pics", exist_ok=True)
            
            svg_file = f"{output_dir}/pics/figure_{i+1}.svg"
            pdf_file = f"{output_dir}/pics/figure_{i+1}.pdf"
            
            # 保存SVG文件
            with open(svg_file, 'w', encoding='utf-8') as f:
                f.write(svg_code)
            
            # 转换SVG到PDF
            debug_print(f"尝试将SVG转换为PDF: figure_{i+1}.svg")
            
            try:
                # 使用不同的工具尝试转换
                # 首先尝试使用cairosvg（通常需要安装）
                try:
                    import cairosvg
                    cairosvg.svg2pdf(file_obj=open(svg_file, 'rb'), write_to=pdf_file)
                    debug_print(f"成功将SVG转换为PDF: figure_{i+1}.pdf")
                except (ImportError, Exception) as e:
                    # 如果cairosvg不可用，尝试使用Inkscape
                    if shutil.which('inkscape'):
                        os.system(f'inkscape -z -D --file="{svg_file}" --export-pdf="{pdf_file}"')
                        debug_print(f"成功将SVG转换为PDF: figure_{i+1}.pdf")
                    # 如果Inkscape不可用，尝试使用rsvg-convert
                    elif shutil.which('rsvg-convert'):
                        os.system(f'rsvg-convert -f pdf -o "{pdf_file}" "{svg_file}"')
                        debug_print(f"成功将SVG转换为PDF: figure_{i+1}.pdf")
                    else:
                        debug_print(f"警告: 无法转换SVG到PDF，请安装cairosvg、Inkscape或rsvg-convert")
                
                # 记录PDF文件信息
                if os.path.exists(pdf_file):
                    SVG_FILES.append({
                        'index': i+1,
                        'path': f"pics/figure_{i+1}.pdf",
                        'caption': title
                    })
            except Exception as e:
                debug_print(f"警告: SVG转换时出错: {str(e)}")
        
        return True
    except Exception as e:
        print(f"提取标题和图像时出错: {str(e)}")
        return False

if __name__ == '__main__':
    main() 