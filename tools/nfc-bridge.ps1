<#
.SYNOPSIS
  Puente NFC: lee la tarjeta del lector USB ACR122U y notifica el toque a la app del laboratorio.

.DESCRIPTION
  La app no puede hablar con el lector por si sola (el lector está en el host, la app en Docker),
  asi que este script hace de intermediario:
    1. Lee el UID de la tarjeta con PC/SC (winscard.dll).
    2. Cuando detecta una tarjeta nueva envia el UID a POST /nfc/tap.
    3. La app contrasta el UID con su lista blanca y deja el toque pendiente.
    4. El navegador, que esta consultando /nfc/poll, consume el toque y abre sesion.

  En esta maquina SCardListReaders() revienta el proceso (bug del Resource Manager de Windows
  con este lector), asi que el nombre del lector se toma del registro "Calais".

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\tools\nfc-bridge.ps1 -Token "mi-token" -AppUrl "http://127.0.0.1:8000"

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\tools\nfc-bridge.ps1 -PrintUid
#>
param(
  [string]$AppUrl = "http://127.0.0.1:8000",
  [string]$Token = $env:NFC_BRIDGE_TOKEN,
  [int]$IntervalSeconds = 2,
  [switch]$PrintUid,
  [switch]$NoSend
)

$ErrorActionPreference = "Continue"

if (-not $PrintUid -and -not $NoSend -and [string]::IsNullOrWhiteSpace($Token)) {
  Write-Host "Falta el token del puente. Usa -Token o la variable de entorno NFC_BRIDGE_TOKEN." -ForegroundColor Red
  exit 1
}

$src = @"
using System;using System.Text;using System.Runtime.InteropServices;
public class NFC {
  [DllImport("winscard.dll")] public static extern int SCardEstablishContext(uint s, IntPtr a, IntPtr b, out IntPtr c);
  [DllImport("winscard.dll", CharSet=CharSet.Unicode, EntryPoint="SCardConnectW")]
  public static extern int SCardConnectW(IntPtr h, string name, uint share, uint proto, out IntPtr card, out uint proto2);
  [DllImport("winscard.dll", CharSet=CharSet.Unicode, EntryPoint="SCardStatusW")]
  public static extern int SCardStatusW(IntPtr card, IntPtr name, ref uint n, out uint state, out uint proto, IntPtr atr, ref uint atrLen);
  [DllImport("winscard.dll", CharSet=CharSet.Unicode, EntryPoint="SCardTransmit")]
  public static extern int SCardTransmit(IntPtr card, ref SCIO s, IntPtr send, uint slen, IntPtr r, IntPtr recv, ref uint rlen);
  [DllImport("winscard.dll")] public static extern int SCardDisconnect(IntPtr card, uint d);
  [DllImport("winscard.dll")] public static extern int SCardReleaseContext(IntPtr c);
  [StructLayout(LayoutKind.Sequential)] public struct SCIO { public int dwProtocol; public int cbPciLength; }
}
"@
if (-not ("NFC" -as [type])) { Add-Type -TypeDefinition $src -ErrorAction Stop }

function Get-ReaderNames {
  $names = @(Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Cryptography\Calais\Readers' -ErrorAction SilentlyContinue | ForEach-Object { $_.PSChildName })
  if ($names.Count -eq 0) { $names = @('ACS ACR122U PICC Interface 0') }
  return $names
}

# Devuelve @{ Uid = "0FC728C9"; Raw = "C928C70F"; Atr = "..." } o $null si no hay tarjeta.
function Read-Card {
  $ctx = [IntPtr]::Zero
  if ([NFC]::SCardEstablishContext(0, [IntPtr]::Zero, [IntPtr]::Zero, [ref]$ctx) -ne 0) { return $null }
  $card = [IntPtr]::Zero; $proto = [uint32]0; $reader = $null
  foreach ($name in (Get-ReaderNames)) {
    if ([NFC]::SCardConnectW($ctx, $name, 0x2, 2, [ref]$card, [ref]$proto) -eq 0) { $reader = $name; break }
  }
  if (-not $reader) { [void][NFC]::SCardReleaseContext($ctx); return $null }

  $nameBuf = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(512)
  $atrBuf = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(64)
  $nameLen = [uint32]512; $atrLen = [uint32]33
  $state = [uint32]0; $proto2 = [uint32]0
  [void][NFC]::SCardStatusW($card, $nameBuf, [ref]$nameLen, [ref]$state, [ref]$proto2, $atrBuf, [ref]$atrLen)
  $atr = [byte[]]::new([int]$atrLen)
  [System.Runtime.InteropServices.Marshal]::Copy($atrBuf, $atr, 0, [int]$atrLen)

  $io = New-Object NFC+SCIO
  $io.dwProtocol = [int]$proto
  $io.cbPciLength = [System.Runtime.InteropServices.Marshal]::SizeOf($io)
  $send = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(64)
  $recv = [System.Runtime.InteropServices.Marshal]::AllocHGlobal(1024)
  $apdu = [byte[]]@(0xFF, 0xCA, 0x00, 0x00, 0x00)
  [System.Runtime.InteropServices.Marshal]::Copy($apdu, 0, $send, $apdu.Length)
  $recvLen = [uint32]1024
  $rc = [NFC]::SCardTransmit($card, [ref]$io, $send, [uint32]$apdu.Length, [IntPtr]::Zero, $recv, [ref]$recvLen)

  $result = $null
  if ($rc -eq 0 -and $recvLen -ge 3) {
    $data = [byte[]]::new([int]$recvLen)
    [System.Runtime.InteropServices.Marshal]::Copy($recv, $data, 0, [int]$recvLen)
    if ($data[0] -ne 0x63 -and $data[0] -ne 0x6A -and $data[0] -ne 0x6B) {
      $uidBytes = [byte[]]$data[0..([int]$recvLen - 3)]
      $be = [byte[]]$uidBytes.Clone(); [Array]::Reverse($be)
      $result = @{
        Uid  = (($be  | ForEach-Object { $_.ToString('X2') }) -join '')
        Raw  = (($uidBytes | ForEach-Object { $_.ToString('X2') }) -join '')
        Atr  = [BitConverter]::ToString($atr, 0, [int]$atrLen)
      }
    }
  }

  [System.Runtime.InteropServices.Marshal]::FreeHGlobal($send)
  [System.Runtime.InteropServices.Marshal]::FreeHGlobal($recv)
  [System.Runtime.InteropServices.Marshal]::FreeHGlobal($atrBuf)
  [System.Runtime.InteropServices.Marshal]::FreeHGlobal($nameBuf)
  [void][NFC]::SCardDisconnect($card, 0)
  [void][NFC]::SCardReleaseContext($ctx)
  return $result
}

function Send-Tap([string]$uid) {
  $body = @{ uid = $uid; source = "bridge-win" } | ConvertTo-Json -Compress
  try {
    $response = Invoke-RestMethod -Uri "$AppUrl/nfc/tap" -Method Post -Headers @{ Authorization = "Bearer $Token" } -ContentType "application/json" -Body $body -TimeoutSec 10
    Write-Host ("  [OK] {0} -> {1}" -f $uid, $response.user) -ForegroundColor Green
    return $true
  } catch {
    $status = 0
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) { $status = [int]$_.Exception.Response.StatusCode }
    if ($status -eq 403) { Write-Host ("  [DENEGADO] {0}: tarjeta no registrada en la app" -f $uid) -ForegroundColor Yellow }
    elseif ($status -eq 401) { Write-Host "  [ERROR] token del puente incorrecto" -ForegroundColor Red }
    elseif ($status -eq 0) { Write-Host ("  [ERROR] la app no responde en {0}" -f $AppUrl) -ForegroundColor Red }
    else { Write-Host ("  [ERROR] HTTP {0}: {1}" -f $status, $_.Exception.Message) -ForegroundColor Red }
    return $false
  }
}

if ($PrintUid) {
  $card = Read-Card
  if ($card) {
    Write-Host ""
    Write-Host "  ATR       : $($card.Atr)" -ForegroundColor Cyan
    Write-Host "  UID (raw) : $($card.Raw)" -ForegroundColor Green
    Write-Host "  UID (est.): $($card.Uid)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Registra la tarjeta con:" -ForegroundColor Gray
    Write-Host "    docker compose exec app python -m app.nfc_cli --uid $($card.Uid) --user admin@example.test" -ForegroundColor Gray
    Write-Host ""
  } else {
    Write-Host "No se detecto tarjeta en el lector." -ForegroundColor Yellow
  }
  exit 0
}

Write-Host ""
Write-Host "  Puente NFC activo" -ForegroundColor Cyan
Write-Host "  App   : $AppUrl" -ForegroundColor Cyan
Write-Host "  Lector: $((Get-ReaderNames) -join ', ')" -ForegroundColor Cyan
Write-Host "  Ctrl+C para detener." -ForegroundColor DarkGray
Write-Host ""

$lastUid = $null
while ($true) {
  $card = Read-Card
  if ($card) {
    if ($card.Uid -ne $lastUid) {
      Write-Host ("  Tarjeta detectada: {0}" -f $card.Uid) -ForegroundColor White
      if (-not $NoSend) { [void](Send-Tap $card.Uid) }
      $lastUid = $card.Uid
    }
  } else {
    if ($lastUid) { Write-Host "  Tarjeta retirada" -ForegroundColor DarkGray }
    $lastUid = $null
  }
  Start-Sleep -Seconds $IntervalSeconds
}
