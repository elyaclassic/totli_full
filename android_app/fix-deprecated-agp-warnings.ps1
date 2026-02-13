# Deprecated Android Gradle Plugin sozlamalarini olib tashlash
# Bu skript C:\Users\<USER>\.gradle\gradle.properties faylini tekshiradi va
# AGP 10.0 da olib tashlanadigan deprecated qatorlarni o'chiradi.

$gradleDir = "$env:USERPROFILE\.gradle"
$gradleProps = "$gradleDir\gradle.properties"

$deprecated = @(
    "android.usesSdkInManifest.disallowed",
    "android.sdk.defaultTargetSdkToCompileSdkIfUnset",
    "android.enableAppCompileTimeRClass",
    "android.builtInKotlin",
    "android.newDsl",
    "android.r8.optimizedResourceShrinking",
    "android.defaults.buildfeatures.resvalues"
)

Write-Host "=== Deprecated AGP sozlamalari tekshirilmoqda ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $gradleProps)) {
    Write-Host "Global gradle.properties topilmadi: $gradleProps" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Ogohlantirishlar boshqa joydan kelishi mumkin. Quyidagilarni sinab ko'ring:" -ForegroundColor Yellow
    Write-Host "1. Android Studio: File -> Invalidate Caches / Restart -> Invalidate and Restart"
    Write-Host "2. Gradle daemon to'xtatish: gradlew --stop (loyiha papkasida)"
    Write-Host "3. .gradle va build papkalarini o'chirish (loyiha ichida), keyin Sync"
    exit 0
}

$content = Get-Content $gradleProps -Raw
$lines = Get-Content $gradleProps
$removed = @()
$newLines = @()

foreach ($line in $lines) {
    $trimmed = $line.Trim()
    $isDeprecated = $false
    foreach ($d in $deprecated) {
        if ($trimmed -like "$d=*") {
            $removed += $trimmed
            $isDeprecated = $true
            break
        }
    }
    if (-not $isDeprecated) { $newLines += $line }
}

if ($removed.Count -eq 0) {
    Write-Host "Deprecated sozlamalar global faylda topilmadi." -ForegroundColor Green
    Write-Host "Ogohlantirishlarni olib tashlash uchun: File -> Invalidate Caches / Restart"
    exit 0
}

$backup = "$gradleProps.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $gradleProps $backup -Force
Write-Host "Backup: $backup" -ForegroundColor Cyan
foreach ($r in $removed) { Write-Host "  O'chirildi: $r" -ForegroundColor Red }
$newLines | Set-Content $gradleProps -Encoding UTF8
Write-Host ""
Write-Host "Tayyor. Android Studio ni qayta ishga tushiring va Sync qiling." -ForegroundColor Green
