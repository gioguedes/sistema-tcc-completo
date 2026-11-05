# Compilar o firmware pela linha de comando

O Arduino IDE 2.x embute um `arduino-cli` completo. Dá para compilar (e verificar erros)
sem abrir a interface — útil para conferir uma alteração antes de ir para a bancada.

```powershell
$cli = "$env:LOCALAPPDATA\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe"
$env:ARDUINO_DIRECTORIES_DATA = "$env:LOCALAPPDATA\Arduino15"
$env:ARDUINO_DIRECTORIES_USER = "$env:USERPROFILE\Documents\Arduino"
& $cli compile --fqbn esp32:esp32:esp32 firmware\no_sensor
```

- `--fqbn esp32:esp32:esp32` = a placa "ESP32 Dev Module" (a DevKitC de 38 pinos).
  **Não** é `esp32:esp32:esp32s3`.
- `--warnings all --clean` para uma verificação mais rigorosa (recompila tudo do zero).
- Trocar o último argumento pelo caminho de qualquer sketch, inclusive os de
  `firmware/testes/`.

## Gravar pela linha de comando (opcional)

```powershell
& $cli upload -p COM3 --fqbn esp32:esp32:esp32 firmware\no_sensor
& $cli monitor -p COM3 -c baudrate=115200
```

O Serial Monitor do IDE e o `monitor` do CLI disputam a porta — só um por vez.

## Gravação exige o botão BOOT nesta placa (17/08/2026)

O auto-reset desta DevKitC parou de funcionar: o esptool reseta a placa (o pulso
em RTS→EN funciona), mas o GPIO0 não vai a nível baixo, e a gravação morre com

```
A fatal error occurred: Failed to connect to ESP32: Wrong boot mode detected (0x13)!
```

`boot:0x13` = `SPI_FAST_FLASH_BOOT`, ou seja, a placa bootou normal em vez de entrar
em modo de gravação.

**Contorno antigo (frágil):** apertar e **segurar** o botão `BOOT`, disparar o
upload e soltar depois do primeiro `Writing at 0x...`. Depende de acertar o
timing e falhou três vezes seguidas em 31/08 — o reset do próprio esptool tira a
placa do modo download.

## Gravar sem depender de timing (2026-08-31) — usar este

O `arduino-cli upload` sempre manda o esptool resetar a placa
(`--before default-reset`), e nesta placa esse reset a tira do modo download.
Chamando o **esptool direto** com `--before no-reset`, ele não encosta no EN:
basta deixar a placa em modo download antes, com calma, e disparar.

Sequência para o usuário, sem pressa nenhuma (o OLED apaga e a placa fica parada
— é o esperado; ela continua assim até o próximo reset):

1. segurar o `BOOT`
2. com o `BOOT` segurado, tocar e soltar o `EN`
3. soltar o `BOOT`

Depois, compilar normalmente e gravar com o esptool direto. Os caminhos abaixo
usam `Join-Path` para não depender de escape de barra invertida:

```powershell
$a15     = $env:LOCALAPPDATA + "\Arduino15"
$esptool = $a15 + "\packages\esp32\tools\esptool_py\5.3.0\esptool.exe"
$boot0   = $a15 + "\packages\esp32\hardware\esp32\3.3.10\tools\partitions\boot_app0.bin"
# build-dir do sketch: sai no `arduino-cli upload -v`, sob %LOCALAPPDATA%\arduino\sketches\<hash>
$d       = "C:\Users\rafael\AppData\Local\arduino\sketches\34ECF157ED9E6E02CFB2743DE9011793"

& $esptool --chip esp32 --port COM3 --baud 460800 --before no-reset --after hard-reset `
  write-flash -z --flash-mode keep --flash-freq keep --flash-size keep `
  0x1000  ($d + "\no_sensor.ino.bootloader.bin") `
  0x8000  ($d + "\no_sensor.ino.partitions.bin") `
  0xe000  $boot0 `
  0x10000 ($d + "\no_sensor.ino.bin")
```

Para descobrir o `build-dir` e os offsets sem adivinhar, rodar uma vez
`arduino-cli upload -p COM3 --fqbn esp32:esp32:esp32 firmware\no_sensor -v`: ele
imprime a linha completa do esptool antes de tentar (e falhar). Os quatro
`Hash of data verified` no fim confirmam a gravação.

⚠️ O `--after hard-reset` do esptool **não reinicia esta placa** (é o mesmo
auto-reset quebrado). Depois de gravar, resetar por software ao abrir a porta
serial, com o pulso de RTS da seção abaixo.

## Ler o Serial pela linha de comando

`arduino-cli monitor` **não funciona** com a saída redirecionada (devolve vazio).
Para capturar o Serial em script, abrir a porta direto pelo .NET:

```powershell
$port = New-Object System.IO.Ports.SerialPort 'COM3',115200,'None',8,'One'
$port.Open()
# reset sem entrar em download mode (mesma sequencia do esptool):
$port.DtrEnable = $false; $port.RtsEnable = $true
Start-Sleep -Milliseconds 120
$port.RtsEnable = $false
$sb = New-Object System.Text.StringBuilder
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt 14) {
  $t = $port.ReadExisting(); if ($t) { [void]$sb.Append($t) }
  Start-Sleep -Milliseconds 100
}
$port.Close(); Write-Output $sb.ToString()
```

Assim dá para resetar a placa por software e capturar o boot inteiro, sem depender
do Serial Monitor do IDE (que aliás disputa a porta).

## ⚠️ Backlog corrompido do driver CP210x (31/08/2026)

Ao **reabrir** a porta depois de ela ter ficado fechada com a placa transmitindo,
o driver despeja um bloco enorme de dados repetidos e truncados — tipicamente a
cauda da última linha, como `idez":33.04}` repetida centenas de milhares de
vezes. Isso imita com perfeição o flood de laço apertado corrigido em 23/08 e já
provocou **duas** caçadas a um bug que não existe.

Como distinguir, em ordem de custo:

1. **Carimbar cada linha com o relógio do PC** durante a captura. O backlog chega
   todo com o mesmo carimbo (`[0,0s]`); o tráfego real aparece espaçado no tempo.
   Foi isto que resolveu.
2. **Conferir a taxa contra o limite físico do baud.** 115200 8N1 comporta no
   máximo ~11,5 KB/s. Medido no episódio: 6,2 MB "em 40 s" e 434 KB "em 3 s" —
   12× acima do que a UART consegue entregar, logo não vinha da UART em tempo real.
3. **Descartar o que chegar nos primeiros ~200 ms** após abrir a porta
   (`ReadExisting` + `DiscardInBuffer` em laço) antes de começar a valer a captura.

Modelo de captura já com carimbo de hora e descarte inicial:

```powershell
$port = New-Object System.IO.Ports.SerialPort 'COM3',115200,'None',8,'One'
$port.DtrEnable = $false; $port.RtsEnable = $false
$port.ReadBufferSize = 262144
$port.Open()
$sw0 = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw0.Elapsed.TotalSeconds -lt 3) { [void]$port.ReadExisting(); $port.DiscardInBuffer(); Start-Sleep -Milliseconds 50 }
$sb = New-Object System.Text.StringBuilder
$saida = New-Object System.Collections.Generic.List[string]
$sw = [System.Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt 200) {
  $t = $port.ReadExisting()
  if ($t) {
    [void]$sb.Append($t)
    $p = $sb.ToString() -split "`n"
    for ($i = 0; $i -lt $p.Count - 1; $i++) {
      $l = $p[$i].Trim()
      if ($l -ne '' -and $l.Length -lt 250) { $saida.Add(("[{0,6:N1}s] {1}" -f $sw.Elapsed.TotalSeconds, $l)) }
    }
    [void]$sb.Clear(); [void]$sb.Append($p[-1])
  }
  Start-Sleep -Milliseconds 100
}
$port.Close()
$saida -join "`n"
```

Para mandar um comando de bancada (`ler`, `queda`, `buffer`) no meio da captura,
basta `$port.WriteLine("ler")` depois do descarte inicial.

## Só ASCII nos sketches

Acento e travessão saem como `???` no Serial. Manter comentários e mensagens em
ASCII puro.
