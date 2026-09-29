$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$updater = Join-Path $repoRoot "update.bat"
$outputFile = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString() + ".log")
$headBefore = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the starting Git commit."
}

$previousNoBrowser = $env:CATALOG_NO_BROWSER
$env:CATALOG_NO_BROWSER = "1"
try {
    $command = 'call "{0}" /local > "{1}" 2>&1' -f $updater, $outputFile
    & $env:ComSpec /d /c $command
    $exitCode = $LASTEXITCODE
    $output = Get-Content -LiteralPath $outputFile -Raw
    Write-Output $output

    if ($exitCode -ne 0) {
        throw "update.bat failed with exit code $exitCode."
    }
    if ($output -notmatch "Loaded 1412 items") {
        throw "The updater did not build all 1412 catalog rows."
    }
    if ($output -notmatch "rebuilt and tested locally") {
        throw "The updater did not reach the expected local result."
    }
    $headAfter = (& git -C $repoRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $headAfter -ne $headBefore) {
        throw "The local smoke test unexpectedly changed the Git commit."
    }
    foreach ($page in @("index.html", "photo_catalog.html", "print_catalog.html")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $page) -PathType Leaf)) {
            throw "The updater did not generate $page."
        }
    }
}
finally {
    $env:CATALOG_NO_BROWSER = $previousNoBrowser
    Remove-Item -LiteralPath $outputFile -Force -ErrorAction SilentlyContinue
}
