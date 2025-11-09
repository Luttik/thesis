# Build script for thesis compilation using Pandoc
# Usage: .\build-thesis.ps1

Write-Host "Building thesis..." -ForegroundColor Green

# Create output directory
New-Item -ItemType Directory -Path "output" -Force | Out-Null

# Change to thesis directory (where the YAML files expect to run from)
Push-Location thesis

# Build PDF
Write-Host "`nGenerating PDF..." -ForegroundColor Cyan
pandoc -d pandoc-pdf.yaml
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ PDF generated: output\thesis.pdf" -ForegroundColor Green
} else {
    Write-Host "✗ PDF generation failed" -ForegroundColor Red
}

# Build Word document
Write-Host "`nGenerating Word document..." -ForegroundColor Cyan
pandoc -d pandoc-docx.yaml
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Word generated: output\thesis.docx" -ForegroundColor Green
} else {
    Write-Host "✗ Word generation failed" -ForegroundColor Red
}

# Return to original directory
Pop-Location

Write-Host "`nDone! Files are in the 'output' directory." -ForegroundColor Green
