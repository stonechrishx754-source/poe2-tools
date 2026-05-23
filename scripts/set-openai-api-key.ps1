$ErrorActionPreference = "Stop"

$secure = Read-Host "Paste OPENAI_API_KEY" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($key)) {
        throw "OPENAI_API_KEY cannot be empty."
    }

    [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $key, "User")
    $env:OPENAI_API_KEY = $key
    Write-Host "OPENAI_API_KEY saved for the current Windows user." -ForegroundColor Green
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}
