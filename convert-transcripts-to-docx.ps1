# Convert all Markdown transcripts to DOCX using pandoc.
# Run from project root: .\convert-transcripts-to-docx.ps1

$ErrorActionPreference = "Stop"
$transcriptsDir = Join-Path $PSScriptRoot "transcripts"
$mdFiles = Get-ChildItem -Path $transcriptsDir -Filter "*.md" -File

if ($mdFiles.Count -eq 0) {
    Write-Host "No .md files found in transcripts." -ForegroundColor Yellow
    exit 0
}

foreach ($md in $mdFiles) {
    $docxName = [System.IO.Path]::ChangeExtension($md.Name, "docx")
    $docxPath = Join-Path $transcriptsDir $docxName
    Write-Host "Converting: $($md.Name) -> $docxName"
    pandoc $md.FullName -o $docxPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "pandoc failed for $($md.Name)"
    }
}

Write-Host "Done. $($mdFiles.Count) file(s) converted." -ForegroundColor Green
