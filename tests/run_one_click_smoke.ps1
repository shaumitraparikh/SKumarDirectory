$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$updater = Join-Path $repoRoot "1_Click_Update.bat"
$inputFile = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString() + ".txt")
$outputFile = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString() + ".log")
$headBefore = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to read the starting Git commit."
}

[System.IO.File]::WriteAllText($inputFile, "N`r`nx`r`n", [System.Text.Encoding]::ASCII)
$previousNoBrowser = $env:CATALOG_NO_BROWSER
$env:CATALOG_NO_BROWSER = "1"
try {
    $command = 'call "{0}" < "{1}" > "{2}" 2>&1' -f $updater, $inputFile, $outputFile
    & $env:ComSpec /d /c $command
    $exitCode = $LASTEXITCODE
    $output = Get-Content -LiteralPath $outputFile -Raw
    Write-Output $output

    if ($exitCode -ne 0) {
        throw "1_Click_Update.bat failed with exit code $exitCode."
    }
    if ($output -notmatch "Loaded 1412 items") {
        throw "The one-click updater did not build all 1412 catalog rows."
    }
    if ($output -notmatch "Catalogs were rebuilt and tested, but not committed or pushed") {
        throw "The one-click updater did not reach the expected safe no-publish result."
    }
    $headAfter = (& git -C $repoRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $headAfter -ne $headBefore) {
        throw "The no-publish smoke test unexpectedly changed the Git commit."
    }
    foreach ($page in @("index.html", "customer_catalog.html", "print_catalog.html")) {
        if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $page) -PathType Leaf)) {
            throw "The one-click updater did not generate $page."
        }
    }
}
finally {
    $env:CATALOG_NO_BROWSER = $previousNoBrowser
    Remove-Item -LiteralPath $inputFile -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $outputFile -Force -ErrorAction SilentlyContinue
}
