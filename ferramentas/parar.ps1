# Encerra os serviços iniciados por demonstracao.sh ou ensaio.sh, sem tocar no banco.
# No Windows o kill do bash não alcança os filhos, e os laços reiniciam quem morre: os laços saem primeiro.
$todos = Get-CimInstance Win32_Process -Filter "Name='bash.exe' OR Name='python.exe' OR Name='node.exe' OR Name='cmd.exe'"
$lacos = $todos | Where-Object { $_.Name -eq 'bash.exe' -and $_.CommandLine -match 'ferramentas[/\\](demonstracao|ensaio)\.sh' }
$lacos | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
$servicos = $todos | Where-Object { $_.CommandLine -match 'sistema-tcc-completo[/\\]|vite(\.js)? +(bin[/\\]vite\.js +)?--port 5173|npx.* vite ' }
$servicos | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
"encerrados: $(@($lacos).Count) laços e $(@($servicos).Count) serviços"
