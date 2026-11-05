# Gera os .stl (para o Bambu Studio) e as imagens .png de cada peca.
# Uso: powershell -ExecutionPolicy Bypass -File gerar.ps1 [peca ...]
param([string[]]$Pecas)

$openscad = "C:\Program Files\OpenSCAD\openscad.com"
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$todas = "base", "tampa", "gancho", "parafuso", "suporte_presilha", "suporte_braco",
         "prova_tampa", "prova_base", "prova_gancho", "prova_suporte"
if (-not $Pecas) { $Pecas = $todas + "montagem" }

New-Item -ItemType Directory -Force "$aqui\stl", "$aqui\render" | Out-Null
$falhas = 0
foreach ($p in $Pecas) {
  # o PowerShell 5.1 tira as aspas internas ao chamar um .exe; a barra as preserva
  $def = "peca=\`"$p\`""
  if ($p -ne "montagem") {
    & $openscad -o "$aqui\stl\$p.stl" -D $def "$aqui\caixa.scad" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Output "FALHOU: $p"; $falhas++; continue }
  }
  & $openscad -o "$aqui\render\$p.png" -D $def --imgsize=1200,900 --autocenter --viewall `
    --colorscheme=Tomorrow "$aqui\caixa.scad" 2>&1 | Out-Null
  Write-Output "ok: $p"
}
if ($falhas) { exit 1 }
