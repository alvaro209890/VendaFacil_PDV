param([string[]]$Cenas)
$ErrorActionPreference='Stop'
foreach($valor in $Cenas) {
  $cena=$valor.PadLeft(2,'0')
  & npx --yes --package '@playwright/cli' playwright-cli '-s=tutorial-pdv' video-start "output/playwright/tutorial-xml/$cena.webm" --size=1440x720 --fps=20 --cursor
  if($LASTEXITCODE -ne 0) {throw 'Falha ao iniciar gravação'}
  try {
    & npx --yes --package '@playwright/cli' playwright-cli '-s=tutorial-pdv' run-code --filename "output/playwright/tutorial-xml/$cena.js"
    if($LASTEXITCODE -ne 0) {throw "Falha na cena $cena"}
  } finally {
    & npx --yes --package '@playwright/cli' playwright-cli '-s=tutorial-pdv' video-stop
  }
  if($LASTEXITCODE -ne 0) {throw 'Falha ao concluir gravação'}
}
