# Check if PostgreSQL is reachable on 127.0.0.1:5432 (Windows).
# Run before starting the app to avoid "database connection" errors.
# Usage: .\scripts\check_postgres.ps1   or   pwsh -File scripts\check_postgres.ps1

$Host = "127.0.0.1"
$Port = 5432

Write-Host "Checking PostgreSQL at ${Host}:${Port}..." -ForegroundColor Cyan

try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($Host, $Port)
    $tcp.Close()
    Write-Host "OK: PostgreSQL is listening on ${Host}:${Port}." -ForegroundColor Green
    exit 0
} catch {
    Write-Host "FAIL: Cannot connect to ${Host}:${Port}. Is PostgreSQL running?" -ForegroundColor Red
    Write-Host "  Windows: Start the 'postgresql-x64-*' service or run pg_ctl." -ForegroundColor Yellow
    Write-Host "  Or run: Get-Service -Name '*postgres*'  then  Start-Service <ServiceName>" -ForegroundColor Yellow
    exit 1
}
