# Подготовка файлов для GitHub Release (локально).
# Запускать после build.py.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$version = python -c "import version; print(version.__version__)"
$dist = Join-Path $PSScriptRoot "dist"
$installerVersioned = Join-Path $dist "ChatList-$version-setup.exe"
$installerLatest = Join-Path $dist "ChatList-setup.exe"
$exe = Join-Path $dist "ChatList.exe"
$checksums = Join-Path $dist "SHA256SUMS.txt"

if (-not (Test-Path $installerVersioned)) {
    Write-Error "Не найден $installerVersioned. Сначала выполните: python .\build.py"
}

Copy-Item $installerVersioned $installerLatest -Force

$lines = @()
foreach ($file in @($exe, $installerVersioned, $installerLatest)) {
    if (Test-Path $file) {
        $hash = (Get-FileHash $file -Algorithm SHA256).Hash
        $name = Split-Path $file -Leaf
        $lines += "$hash  $name"
    }
}
$lines | Set-Content $checksums -Encoding utf8

Write-Host ""
Write-Host "Артефакты готовы для GitHub Release v$version"
Write-Host "  $installerLatest"
Write-Host "  $installerVersioned"
Write-Host "  $exe"
Write-Host "  $checksums"
Write-Host ""
Write-Host "Публикация через gh CLI:"
Write-Host "  gh release create v$version --title `"ChatList $version`" --notes-file .github\release-notes\v$version.md dist\ChatList-setup.exe dist\ChatList-$version-setup.exe dist\ChatList.exe dist\SHA256SUMS.txt"
Write-Host ""
Write-Host "Или push тега для автоматической сборки:"
Write-Host "  git tag v$version"
Write-Host "  git push origin v$version"
