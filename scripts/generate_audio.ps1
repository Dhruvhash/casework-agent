Add-Type -AssemblyName System.Speech
$scenes = Get-Content -Raw -Path "docs\demo\scenes.json" | ConvertFrom-Json

$i = 0
foreach ($s in $scenes) {
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $synth.Rate = -1
    $wavPath = [System.IO.Path]::GetFullPath("docs\demo\audio_$i.wav")
    if (Test-Path $wavPath) { Remove-Item $wavPath -Force }
    $synth.SetOutputToWaveFile($wavPath)
    $synth.Speak($s.text)
    $synth.Dispose()
    Write-Host "Generated $i.wav for $($s.title)"
    $i++
}
Write-Host "All narration audio generated successfully!"
