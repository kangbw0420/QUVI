# 색상 정의 함수
function Write-ColorText {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

Write-ColorText "===========================================" "Green"
Write-ColorText "  Spring Boot Build & Run" "Green"
Write-ColorText "===========================================" "Green"
Write-Host ""

# 프로필 선택
Write-ColorText "실행할 프로필을 선택하세요:" "Yellow"
Write-Host "1) daquv"
Write-Host "2) dev"
Write-Host "3) prod"
Write-Host ""
$choice = Read-Host "선택 (1-3)"

switch ($choice) {
    "1" { $PROFILE = "daquv" }
    "2" { $PROFILE = "dev" }
    "3" { $PROFILE = "prod" }
    default {
        Write-ColorText "잘못된 선택입니다. 1, 2, 3 중에서 선택해주세요." "Red"
        exit 1
    }
}

Write-Host ""
Write-ColorText "선택된 프로필: $PROFILE" "Yellow"
Write-Host ""

# 암호화 비밀번호 입력
Write-ColorText "설정 파일 암호화 비밀번호를 입력하세요:" "Yellow"
Write-ColorText "(또는 Enter를 눌러 런타임에 입력)" "Cyan"
$ENCRYPTION_PASSWORD = Read-Host "암호화 비밀번호" -AsSecureString
$ENCRYPTION_PASSWORD_PLAIN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($ENCRYPTION_PASSWORD))
Write-Host ""

# JAR 파일 찾기
$JAR_FILE = Get-ChildItem -Path "." -Filter "*.jar" -File | Where-Object {
    $_.Name -notlike "*sources.jar" -and $_.Name -notlike "*javadoc.jar"
} | Select-Object -First 1

if (-not $JAR_FILE) {
    Write-ColorText "JAR 파일을 찾을 수 없습니다." "Red"
    Write-ColorText "back_agent 폴더에 JAR 파일이 있는지 확인해주세요." "Yellow"
    exit 1
}

Write-ColorText "백그라운드에서 애플리케이션을 시작합니다..." "Green"
Write-ColorText "JAR 파일: $($JAR_FILE.Name)" "Cyan"
Write-ColorText "Profile: $PROFILE" "Cyan"

# JVM 옵션 구성
$JVM_OPTS = "-Dspring.profiles.active=$PROFILE"

# 암호화 비밀번호가 입력된 경우 JVM 옵션에 추가
if ($ENCRYPTION_PASSWORD_PLAIN -and $ENCRYPTION_PASSWORD_PLAIN.Length -gt 0) {
    $JVM_OPTS += " -Dpass_encryption=$ENCRYPTION_PASSWORD_PLAIN"
    Write-ColorText "암호화 비밀번호가 JVM 옵션에 설정되었습니다." "Cyan"
} else {
    Write-ColorText "런타임에 암호화 비밀번호를 입력해야 합니다." "Yellow"
}

# 백그라운드 실행
$logFile = "back.log"
$processStartInfo = New-Object System.Diagnostics.ProcessStartInfo
$processStartInfo.FileName = "java"
$processStartInfo.Arguments = "-jar $JVM_OPTS $($JAR_FILE.Name)"
$processStartInfo.RedirectStandardOutput = $true
$processStartInfo.RedirectStandardError = $true
$processStartInfo.UseShellExecute = $false
$processStartInfo.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processStartInfo

# 로그 파일로 출력 리디렉션
$process.add_OutputDataReceived({
    param($sender, $e)
    if ($e.Data) {
        Add-Content -Path $logFile -Value $e.Data
    }
})

$process.add_ErrorDataReceived({
    param($sender, $e)
    if ($e.Data) {
        Add-Content -Path $logFile -Value $e.Data
    }
})

# 기존 로그 파일 초기화
if (Test-Path $logFile) {
    Remove-Item $logFile
}

$process.Start() | Out-Null
$process.BeginOutputReadLine()
$process.BeginErrorReadLine()

$NEW_PID = $process.Id

Write-ColorText "애플리케이션이 백그라운드에서 시작되었습니다." "Green"
Write-ColorText "새 PID: $NEW_PID" "Cyan"
Write-Host ""

# 잠시 대기 후 로그 시작 부분 보여주기
Start-Sleep -Seconds 2
Write-ColorText "=== 애플리케이션 시작 로그 ===" "Yellow"
if (Test-Path $logFile) {
    Get-Content $logFile -Head 20
}
Write-Host ""
Write-ColorText "실시간 로그를 보려면: " "Green" -NoNewline
Write-ColorText "Get-Content back.log -Wait" "Cyan"
Write-Host ""

# 사용자 선택 메뉴
while ($true) {
    Write-ColorText "===========================================" "Yellow"
    Write-ColorText "다음 중 선택하세요:" "Yellow"
    Write-Host "1) 실시간 로그 보기 (Get-Content -Wait)"
    Write-Host "2) 애플리케이션 상태 확인"
    Write-Host "3) 최근 로그 100줄 보기"
    Write-Host "4) 애플리케이션 종료"
    Write-Host "5) 스크립트 종료"
    Write-Host ""
    $menu_choice = Read-Host "선택 (1-5)"

    switch ($menu_choice) {
        "1" {
            Write-ColorText "실시간 로그를 시작합니다. Ctrl+C로 중단하세요." "Green"
            if (Test-Path $logFile) {
                Get-Content $logFile -Wait
            } else {
                Write-ColorText "로그 파일이 아직 생성되지 않았습니다." "Yellow"
            }
        }
        "2" {
            try {
                $runningProcess = Get-Process -Id $NEW_PID -ErrorAction Stop
                Write-ColorText "애플리케이션이 정상적으로 실행 중입니다. (PID: $NEW_PID)" "Green"
            } catch {
                Write-ColorText "애플리케이션이 실행되지 않고 있습니다." "Red"
                Write-ColorText "최근 로그를 확인해보세요:" "Yellow"
                if (Test-Path $logFile) {
                    Get-Content $logFile -Tail 10
                }
            }
        }
        "3" {
            Write-ColorText "=== 최근 로그 100줄 ===" "Yellow"
            if (Test-Path $logFile) {
                Get-Content $logFile -Tail 100
            } else {
                Write-ColorText "로그 파일이 없습니다." "Yellow"
            }
        }
        "4" {
            Write-ColorText "애플리케이션을 종료합니다..." "Yellow"
            try {
                Stop-Process -Id $NEW_PID -Force -ErrorAction Stop
                Write-ColorText "애플리케이션이 종료되었습니다." "Green"
            } catch {
                Write-ColorText "프로세스 종료 중 오류가 발생했습니다." "Red"
            }
        }
        "5" {
            Write-ColorText "스크립트를 종료합니다." "Green"
            Write-ColorText "애플리케이션은 백그라운드에서 계속 실행됩니다. (PID: $NEW_PID)" "Cyan"
            exit 0
        }
        default {
            Write-ColorText "잘못된 선택입니다. 1-5 중에서 선택해주세요." "Red"
        }
    }

    Write-Host ""
    Read-Host "계속하려면 Enter를 누르세요..."
    Write-Host ""
}

# 스크립트 종료 시 정리
trap {
    if ($process -and -not $process.HasExited) {
        $process.Kill()
    }
}