$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$root=Split-Path (Split-Path $PSScriptRoot)
$out=Join-Path $root 'output\playwright\tutorial-xml'
$roteiro=Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'roteiro.json') | ConvertFrom-Json
$voz=New-Object System.Speech.Synthesis.SpeechSynthesizer
$voz.SelectVoice('Microsoft Maria Desktop')
$voz.Rate=0
foreach($cena in $roteiro) {
  for($i=0;$i -lt $cena.fala.Count;$i++) {
    $wav=Join-Path $out ($cena.id+'-'+$i+'.wav')
    $voz.SetOutputToWaveFile($wav)
    $voz.Speak([string]$cena.fala[$i])
    $voz.SetOutputToNull()
  }
}
$voz.Dispose()
Write-Output 'Narração pt-BR gerada em arquivos WAV.'
