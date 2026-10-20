# Script hỗ trợ khởi tạo và đẩy repository lên GitHub
$ErrorActionPreference = "Stop"

Write-Host "=== Bắt đầu khởi tạo và chuẩn bị đẩy lên GitHub ===" -ForegroundColor Green

# 1. Khởi tạo Git
if (-not (Test-Path ".git")) {
    Write-Host "[1/10] Khởi tạo Git repository..." -ForegroundColor Cyan
    git init
} else {
    Write-Host "[1/10] Git repository đã được khởi tạo trước đó." -ForegroundColor Yellow
}

# 2. Thêm file cấu hình môi trường Git
Write-Host "[2/10] Commit .gitignore và .editorconfig..." -ForegroundColor Cyan
git add .gitignore .editorconfig
git commit -m "chore: initialize repository with gitignore and editorconfig" --allow-empty

# 3. Lưu trữ lab cũ (Zabbix legacy)
Write-Host "[3/10] Commit legacy Zabbix lab archive..." -ForegroundColor Cyan
git add legacy/
git commit -m "refactor(legacy): preserve initial Zabbix exploratory prototype in legacy archive" --allow-empty

# 4. SNMP Simulator
Write-Host "[4/10] Commit SNMP simulator test target..." -ForegroundColor Cyan
git add simulators/
git commit -m "feat(simulator): add containerized SNMPv2c simulator exposing MIB-II interface metrics" --allow-empty

# 5. Cấu hình Prometheus, Alertmanager, Grafana
Write-Host "[5/10] Commit monitoring configurations and provisioning..." -ForegroundColor Cyan
git add config/
git commit -m "feat(monitoring): add Prometheus scrapers, alert rules, Alertmanager routing, and Grafana provisioning" --allow-empty

# 6. Docker Compose & Environment
Write-Host "[6/10] Commit Docker Compose and environment templates..." -ForegroundColor Cyan
git add deploy/ docker-compose.yml .env.example
git commit -m "feat(deploy): add pinned Docker Compose stack and lab-safe environment template" --allow-empty

# 7. Anomaly Detector
Write-Host "[7/10] Commit statistical anomaly detector..." -ForegroundColor Cyan
git add src/
git commit -m "feat(analytics): implement statistical anomaly detector with rolling z-score and EWMA" --allow-empty

# 8. Testing & CI
Write-Host "[8/10] Commit testing suite, validation scripts and GitHub Actions..." -ForegroundColor Cyan
git add scripts/ tests/ Makefile .github/
git commit -m "test(ci): add cross-platform validator, unit test suite, and GitHub Actions workflow" --allow-empty

# 9. Docs & Metadata
Write-Host "[9/10] Commit thesis documentation, evaluation plan, and citation metadata..." -ForegroundColor Cyan
git add docs/ README.md ROADMAP.md CHANGELOG.md CONTRIBUTING.md SECURITY.md LICENSE CITATION.cff
git commit -m "docs: add academic thesis documentation, architecture diagrams, evaluation plan, and citation metadata" --allow-empty

# 10. Cấu hình remote và nhánh main
Write-Host "[10/10] Cấu hình remote origin và đẩy lên GitHub..." -ForegroundColor Cyan
git branch -M main

$remoteUrl = "https://github.com/nguyen-tri-Cyber/centralized-network-monitoring.git"
git remote remove origin 2>$null
git remote add origin $remoteUrl

Write-Host "`nĐang đẩy lên GitHub ($remoteUrl)..." -ForegroundColor Yellow
Write-Host "LƯU Ý: Nếu đây là lần đầu, trình duyệt hoặc Git Credential Manager có thể hiển thị cửa sổ đăng nhập GitHub." -ForegroundColor Yellow
git push -u origin main

Write-Host "`n=== Hoàn tất đẩy lên GitHub thành công! ===" -ForegroundColor Green
