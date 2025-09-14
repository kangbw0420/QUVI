#!/bin/bash

# Git 작업 자동화 스크립트
# 메인 디렉토리와 5개 하위 디렉토리에서 git 작업을 수행합니다.

# 작업할 디렉토리 목록
DIRECTORIES=(
    "."  # 메인 디렉토리 (현재 디렉토리)
    "front"
    "agent/src/main/java/com/daquv/agent/admin"
    "agent/src/main/java/com/daquv/agent/web"
    "agent/src/main/java/com/daquv/agent/quvi"
    "agent/src/main/java/com/daquv/agent/workflow"
)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 메뉴 표시
show_menu() {
    echo -e "${BLUE}=== Git 작업 자동화 스크립트 ===${NC}"
    echo -e "${YELLOW}작업할 디렉토리:${NC}"
    for dir in "${DIRECTORIES[@]}"; do
        if [ "$dir" = "." ]; then
            echo "  - . (메인 디렉토리)"
        else
            echo "  - $dir"
        fi
    done
    echo ""
    echo -e "${GREEN}선택하세요:${NC}"
    echo "  s - Git Status 확인"
    echo "  p - Git Pull (origin main)"
    echo "  c - Git Commit & Push"
    echo "  q - 종료"
    echo ""
    read -p "선택: " choice
}

# Git Status 확인
git_status() {
    echo -e "${BLUE}=== Git Status 확인 ===${NC}"
    echo ""
    
    for dir in "${DIRECTORIES[@]}"; do
        if [ "$dir" = "." ]; then
            echo -e "${YELLOW}📁 . (메인 디렉토리)${NC}"
        else
            echo -e "${YELLOW}📁 $dir${NC}"
        fi
        echo "----------------------------------------"
        
        if [ -d "$dir" ]; then
            cd "$dir" || continue
            
            # 현재 브랜치 확인
            current_branch=$(git branch --show-current 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo -e "현재 브랜치: ${GREEN}$current_branch${NC}"
                
                # main 브랜치인지 확인
                if [ "$current_branch" = "main" ]; then
                    echo -e "브랜치 상태: ${GREEN}✅ main 브랜치${NC}"
                else
                    echo -e "브랜치 상태: ${RED}❌ main 브랜치가 아님${NC}"
                fi
            else
                echo -e "브랜치 상태: ${RED}❌ Git 리포지토리가 아님${NC}"
                cd - > /dev/null
                continue
            fi
            
            echo ""
            echo "Git Status:"
            git status --porcelain 2>/dev/null
            
            if [ $? -eq 0 ]; then
                # 변경사항이 있는지 확인
                if [ -z "$(git status --porcelain)" ]; then
                    echo -e "${GREEN}✅ 커밋할 변경사항 없음${NC}"
                else
                    echo -e "${YELLOW}⚠️  커밋되지 않은 변경사항 있음${NC}"
                fi
            else
                echo -e "${RED}❌ Git 명령 실행 실패${NC}"
            fi
            
            cd - > /dev/null
        else
            echo -e "${RED}❌ 디렉토리가 존재하지 않음: $dir${NC}"
        fi
        
        echo ""
    done
}

# Git Pull 실행
git_pull() {
    echo -e "${BLUE}=== Git Pull (origin main) ===${NC}"
    echo ""
    
    for dir in "${DIRECTORIES[@]}"; do
        if [ "$dir" = "." ]; then
            echo -e "${YELLOW}📁 . (메인 디렉토리)${NC}"
        else
            echo -e "${YELLOW}📁 $dir${NC}"
        fi
        echo "----------------------------------------"
        
        if [ -d "$dir" ]; then
            cd "$dir" || continue
            
            # Git 리포지토리인지 확인
            if git rev-parse --git-dir > /dev/null 2>&1; then
                echo "Git Pull 실행 중..."
                git pull origin main 2>&1
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✅ Pull 성공${NC}"
                else
                    echo -e "${RED}❌ Pull 실패${NC}"
                fi
            else
                echo -e "${RED}❌ Git 리포지토리가 아님${NC}"
            fi
            
            cd - > /dev/null
        else
            echo -e "${RED}❌ 디렉토리가 존재하지 않음: $dir${NC}"
        fi
        
        echo ""
    done
}

# Git Commit & Push 실행
git_commit_push() {
    echo -e "${BLUE}=== Git Commit & Push ===${NC}"
    echo ""
    
    # 커밋 메시지 입력
    read -p "커밋 메시지를 입력하세요: " commit_message
    
    if [ -z "$commit_message" ]; then
        echo -e "${RED}❌ 커밋 메시지가 비어있습니다.${NC}"
        return 1
    fi
    
    echo ""
    echo -e "${YELLOW}커밋 메시지: \"$commit_message\"${NC}"
    echo ""
    
    for dir in "${DIRECTORIES[@]}"; do
        if [ "$dir" = "." ]; then
            echo -e "${YELLOW}📁 . (메인 디렉토리)${NC}"
        else
            echo -e "${YELLOW}📁 $dir${NC}"
        fi
        echo "----------------------------------------"
        
        if [ -d "$dir" ]; then
            cd "$dir" || continue
            
            # Git 리포지토리인지 확인
            if git rev-parse --git-dir > /dev/null 2>&1; then
                # 변경사항이 있는지 확인
                if [ -n "$(git status --porcelain)" ]; then
                    echo "Git Add 실행 중..."
                    git add . 2>&1
                    
                    echo "Git Commit 실행 중..."
                    git commit -m "$commit_message" 2>&1
                    
                    if [ $? -eq 0 ]; then
                        echo -e "${GREEN}✅ Commit 성공${NC}"
                        
                        echo "Git Push 실행 중..."
                        git push origin main 2>&1
                        
                        if [ $? -eq 0 ]; then
                            echo -e "${GREEN}✅ Push 성공${NC}"
                        else
                            echo -e "${RED}❌ Push 실패${NC}"
                        fi
                    else
                        echo -e "${RED}❌ Commit 실패${NC}"
                    fi
                else
                    echo -e "${YELLOW}⚠️  커밋할 변경사항이 없습니다.${NC}"
                fi
            else
                echo -e "${RED}❌ Git 리포지토리가 아님${NC}"
            fi
            
            cd - > /dev/null
        else
            echo -e "${RED}❌ 디렉토리가 존재하지 않음: $dir${NC}"
        fi
        
        echo ""
    done
}

# 메인 루프
main() {
    while true; do
        show_menu
        
        case $choice in
            s|S)
                git_status
                ;;
            p|P)
                git_pull
                ;;
            c|C)
                git_commit_push
                ;;
            q|Q)
                echo -e "${GREEN}스크립트를 종료합니다.${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}잘못된 선택입니다. s, p, c, q 중에서 선택해주세요.${NC}"
                ;;
        esac
        
        echo ""
        read -p "계속하려면 Enter를 누르세요..."
        clear
    done
}

# 스크립트 실행
main
