#!/bin/bash

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 打印帮助信息的函数
print_help() {
    echo -e "${BLUE}用法: $0 <tex_file_path>${NC}"
    echo -e "  该脚本用于编译LaTeX文件生成PDF"
    echo -e "  例如: $0 gemini_paper/绪论/绪论.tex"
    echo
    echo -e "${YELLOW}选项:${NC}"
    echo -e "  -h, --help     显示帮助信息"
    echo -e "  -c, --clean    清理临时文件（编译后）"
    echo -e "  -o, --open     编译成功后打开PDF文件"
}

# 参数解析
TEX_FILE=""
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
        *.tex)
            TEX_FILE="$arg"
            ;;
    esac
done

# 检查是否提供了tex文件
if [ -z "$TEX_FILE" ]; then
    echo -e "${RED}错误: 必须提供LaTeX文件路径${NC}"
    print_help
    exit 1
fi

# 检查文件是否存在
if [ ! -f "$TEX_FILE" ]; then
    echo -e "${RED}错误: 文件 '$TEX_FILE' 不存在${NC}"
    exit 1
fi

# 提取目录和文件名
TEX_DIR=$(dirname "$TEX_FILE")
TEX_FILENAME=$(basename "$TEX_FILE")
TEX_NAME="${TEX_FILENAME%.tex}"
PDF_FILE="$TEX_DIR/$TEX_NAME.pdf"

echo -e "${BLUE}编译文件: ${YELLOW}$TEX_FILE${NC}"
echo -e "${BLUE}输出目录: ${YELLOW}$TEX_DIR${NC}"

# 切换到LaTeX文件所在目录
CURRENT_DIR=$(pwd)
cd "$TEX_DIR" || { echo -e "${RED}错误: 无法切换到目录 '$TEX_DIR'${NC}"; exit 1; }

# 记录编译前的文件，用于比较
FILES_BEFORE=$(ls -l)

# 显示时间戳
echo -e "${BLUE}[$(date +%H:%M:%S)] 开始第一次编译...${NC}"

# 第一次编译
xelatex -interaction=nonstopmode "$TEX_FILENAME"
COMPILE_STATUS=$?

if [ $COMPILE_STATUS -ne 0 ]; then
    echo -e "${YELLOW}第一次编译返回状态: $COMPILE_STATUS (可能有警告)${NC}"
else
    echo -e "${GREEN}第一次编译成功${NC}"
fi

# 显示时间戳
echo -e "${BLUE}[$(date +%H:%M:%S)] 开始第二次编译...${NC}"

# 第二次编译
xelatex -interaction=nonstopmode "$TEX_FILENAME"
COMPILE_STATUS=$?

if [ $COMPILE_STATUS -ne 0 ]; then
    echo -e "${YELLOW}第二次编译返回状态: $COMPILE_STATUS (可能有警告)${NC}"
else
    echo -e "${GREEN}第二次编译成功${NC}"
fi

# 检查PDF是否生成
if [ -f "${TEX_NAME}.pdf" ]; then
    PDF_SIZE=$(du -h "${TEX_NAME}.pdf" | cut -f1)
    echo -e "${GREEN}成功生成PDF文件: ${YELLOW}$PDF_FILE ${GREEN}(大小: $PDF_SIZE)${NC}"
    
    # 打开PDF文件（如果指定了-o选项）
    if [ "$OPEN_PDF" = true ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            open "${TEX_NAME}.pdf"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            if command -v xdg-open &> /dev/null; then
                xdg-open "${TEX_NAME}.pdf"
            else
                echo -e "${YELLOW}无法自动打开PDF文件: 未找到xdg-open命令${NC}"
            fi
        else
            echo -e "${YELLOW}不支持自动打开PDF文件: 未知操作系统${NC}"
        fi
    fi
else
    echo -e "${RED}错误: 无法找到生成的PDF文件${NC}"
    
    # 检查日志文件中的错误
    if [ -f "${TEX_NAME}.log" ]; then
        echo -e "${YELLOW}检查日志文件中的错误:${NC}"
        grep -n "!" "${TEX_NAME}.log" | head -10
    fi
    
    cd "$CURRENT_DIR"
    exit 1
fi

# 清理临时文件（如果指定了-c选项）
if [ "$CLEAN_TEMP" = true ]; then
    echo -e "${BLUE}清理临时文件...${NC}"
    rm -f "${TEX_NAME}.aux" "${TEX_NAME}.log" "${TEX_NAME}.out" "${TEX_NAME}.toc" \
          "${TEX_NAME}.lof" "${TEX_NAME}.lot" "${TEX_NAME}.bbl" "${TEX_NAME}.blg" \
          "${TEX_NAME}.nav" "${TEX_NAME}.snm" "${TEX_NAME}.synctex.gz"
    echo -e "${GREEN}清理完成${NC}"
fi

# 返回原目录
cd "$CURRENT_DIR"

echo -e "${GREEN}编译过程完成${NC}"
exit 0
