Set-Location "C:\CheekSplittersAnalytics"

python cheek_splitters_engine.py

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

scp -i "$env:USERPROFILE\.ssh\sharpstack_kbo" `
    "C:\CheekSplittersAnalytics\output\cards\kbo_card.json" `
    "sharp@10.10.0.153:/opt/CheekSplittersAnalytics/output/cards/kbo_card.json"

exit $LASTEXITCODE
