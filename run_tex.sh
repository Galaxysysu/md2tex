#!/bin/bash

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 打印帮助信息的函数
print_help() {
    echo -e "${BLUE}用法: $0 <file_path>${NC}"
    echo -e "  该脚本用于将Markdown或LaTeX文件转换为PDF"
    echo -e "  支持的文件类型: .md, .tex"
    echo -e "  例如: $0 gemini_paper/绪论/绪论.tex"
    echo -e "        $0 gemini_paper/绪论.md"
    echo
    echo -e "${YELLOW}选项:${NC}"
    echo -e "  -h, --help     显示帮助信息"
    echo -e "  -c, --clean    清理临时文件（编译后）"
    echo -e "  -o, --open     编译成功后打开PDF文件"
}

# 编译LaTeX文件的函数
compile_tex() {
    local tex_file="$1"
    local tex_dir=$(dirname "$tex_file")
    local tex_filename=$(basename "$tex_file")
    local tex_name="${tex_filename%.tex}"
    local log_file="/tmp/xelatex_$$.log"
    
    # 切换到LaTeX文件所在目录
    cd "$tex_dir" || { echo -e "${RED}错误: 无法切换到目录 '$tex_dir'${NC}"; return 1; }
    
    echo -e "${BLUE}[$(date +%H:%M:%S)] 开始第一次编译...${NC}"
    # 将编译输出重定向到临时日志文件
    xelatex -interaction=nonstopmode "$tex_filename" > "$log_file" 2>&1
    local compile_status=$?
    
    if [ $compile_status -ne 0 ]; then
        echo -e "${YELLOW}第一次编译返回状态: $compile_status (可能有警告)${NC}"
    else
        echo -e "${GREEN}第一次编译成功${NC}"
    fi
    
    echo -e "${BLUE}[$(date +%H:%M:%S)] 开始第二次编译...${NC}"
    # 将编译输出重定向到临时日志文件
    xelatex -interaction=nonstopmode "$tex_filename" > "$log_file" 2>&1
    compile_status=$?
    
    if [ $compile_status -ne 0 ]; then
        echo -e "${YELLOW}第二次编译返回状态: $compile_status (可能有警告)${NC}"
    else
        echo -e "${GREEN}第二次编译成功${NC}"
    fi
    
    # 检查PDF是否生成
    if [ -f "${tex_name}.pdf" ]; then
        local pdf_size=$(du -h "${tex_name}.pdf" | cut -f1)
        echo -e "${GREEN}成功生成PDF文件: ${YELLOW}${tex_dir}/${tex_name}.pdf ${GREEN}(大小: $pdf_size)${NC}"
        # 清理临时日志文件
        rm -f "$log_file"
        return 0
    else
        echo -e "${RED}错误: 无法找到生成的PDF文件${NC}"
        if [ -f "${tex_name}.log" ]; then
            echo -e "${YELLOW}检查日志文件中的错误:${NC}"
            grep -n "!" "${tex_name}.log" | head -10
        fi
        # 清理临时日志文件
        rm -f "$log_file"
        return 1
    fi
}

# 处理Markdown文件的函数
process_markdown() {
    local md_file="$1"
    local md_dir=$(dirname "$md_file")
    local md_filename=$(basename "$md_file")
    local md_name="${md_filename%.md}"
    # 修改tex文件路径，考虑到md2latex_pandoc.py会创建同名文件夹
    local tex_file="${md_dir}/${md_name}/${md_name}.tex"
    local log_file="/tmp/md2latex_$$.log"
    local script_options="--fix-images --quiet"
    
    # 如果需要打开PDF，添加--open选项
    if [ "$OPEN_PDF" = true ]; then
        script_options="$script_options --open"
    fi
    
    echo -e "${BLUE}转换Markdown到LaTeX: ${YELLOW}$md_file${NC}"
    
    # 调用Python脚本转换Markdown到LaTeX，重定向输出
    python md2latex_pandoc.py "$md_file" $script_options > "$log_file" 2>&1
    local convert_status=$?
    if [ $convert_status -ne 0 ]; then
        echo -e "${RED}错误: Markdown转换失败${NC}"
        # 显示错误日志
        cat "$log_file"
        rm -f "$log_file"
        return 1
    fi
    
    # 检查生成的tex文件
    if [ ! -f "$tex_file" ]; then
        echo -e "${RED}错误: 未找到生成的LaTeX文件: $tex_file${NC}"
        cat "$log_file"
        rm -f "$log_file"
        return 1
    fi
    
    # 如果md2latex_pandoc.py已经处理了PDF生成和打开，我们可以直接返回
    if [[ "$script_options" == *"--open"* ]]; then
        pdf_file="${md_dir}/${md_name}/${md_name}.pdf"
        if [ -f "$pdf_file" ]; then
            local pdf_size=$(du -h "$pdf_file" | cut -f1)
            echo -e "${GREEN}成功生成PDF文件: ${YELLOW}${pdf_file} ${GREEN}(大小: $pdf_size)${NC}"
            # 清理临时日志文件
            rm -f "$log_file"
            return 0
        fi
    fi
    
    # 清理临时日志文件
    rm -f "$log_file"
    
    # 如果脚本没有处理PDF生成，使用compile_tex函数
    compile_tex "$tex_file"
    return $?
}

# 清理临时文件的函数
clean_temp_files() {
    local base_name="$1"
    echo -e "${BLUE}清理临时文件...${NC}"
    rm -f "${base_name}.aux" "${base_name}.log" "${base_name}.out" "${base_name}.toc" \
          "${base_name}.lof" "${base_name}.lot" "${base_name}.bbl" "${base_name}.blg" \
          "${base_name}.nav" "${base_name}.snm" "${base_name}.synctex.gz"
    echo -e "${GREEN}清理完成${NC}"
}

# 参数解析
INPUT_FILE=""
CLEAN_TEMP=false
OPEN_PDF=false

for arg in "$@"; do
    case $arg in
        -h|--help)
            print_help
            exit 0
            ;;
        -c|--clean)
            CLEAN_TEMP=true
            ;;
        -o|--open)
            OPEN_PDF=true
            ;;
        *.tex|*.md)
            INPUT_FILE="$arg"
            ;;
    esac
done

# 检查是否提供了输入文件
if [ -z "$INPUT_FILE" ]; then
    echo -e "${RED}错误: 必须提供输入文件路径 (.md 或 .tex)${NC}"
    print_help
    exit 1
fi

# 检查文件是否存在
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}错误: 文件 '$INPUT_FILE' 不存在${NC}"
    exit 1
fi

# 保存当前目录
CURRENT_DIR=$(pwd)

# 根据文件类型进行处理
case "$INPUT_FILE" in
    *.tex)
        compile_tex "$INPUT_FILE"
        COMPILE_STATUS=$?
        ;;
    *.md)
        process_markdown "$INPUT_FILE"
        COMPILE_STATUS=$?
        ;;
    *)
        echo -e "${RED}错误: 不支持的文件类型${NC}"
        exit 1
        ;;
esac

# 如果编译成功且需要清理临时文件
if [ $COMPILE_STATUS -eq 0 ] && [ "$CLEAN_TEMP" = true ]; then
    clean_temp_files "${INPUT_FILE%.*}"
fi

# 如果编译成功且需要打开PDF
if [ $COMPILE_STATUS -eq 0 ] && [ "$OPEN_PDF" = true ]; then
    PDF_FILE="${INPUT_FILE%.*}.pdf"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$PDF_FILE"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$PDF_FILE"
        else
            echo -e "${YELLOW}无法自动打开PDF文件: 未找到xdg-open命令${NC}"
        fi
    else
        echo -e "${YELLOW}不支持自动打开PDF文件: 未知操作系统${NC}"
    fi
fi

# 返回原目录
cd "$CURRENT_DIR"

# 根据编译状态设置退出码
exit $COMPILE_STATUS
