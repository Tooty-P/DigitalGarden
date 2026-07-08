# 使用项目自己的虚拟环境运行 Blooming Spell
# 如果系统 python / py 版本太新，也不会影响这里的运行

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "没有找到 .venv，请先创建虚拟环境并安装依赖。" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot
& $PythonExe "main.py"
