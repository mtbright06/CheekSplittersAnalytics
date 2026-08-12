Set-Location "C:\CheekSplittersAnalytics"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

python cheek_splitters_engine.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

scp -P 2222 -i "$env:USERPROFILE\.ssh\sharpstack_kbo" `
    "C:\CheekSplittersAnalytics\output\cards\kbo_card.json" `
    "sharp@10.10.4.153:/opt/CheekSplittersAnalytics/output/cards/kbo_card.json"

exit $LASTEXITCODE
