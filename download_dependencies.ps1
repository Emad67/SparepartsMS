# Create necessary directories if they don't exist
Write-Host "Creating directories..."
New-Item -ItemType Directory -Force -Path "static/css" -Verbose
New-Item -ItemType Directory -Force -Path "static/js" -Verbose
New-Item -ItemType Directory -Force -Path "static/fonts" -Verbose

# Download Bootstrap CSS
Write-Host "Downloading Bootstrap CSS..."
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" -OutFile "static/css/bootstrap.min.css" -Verbose

# Download Bootstrap Bundle JS
Write-Host "Downloading Bootstrap Bundle JS..."
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" -OutFile "static/js/bootstrap.bundle.min.js" -Verbose

# Download jQuery
Write-Host "Downloading jQuery..."
Invoke-WebRequest -Uri "https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js" -OutFile "static/js/jquery-3.6.0.min.js" -Verbose

# Download jQuery UI CSS
Write-Host "Downloading jQuery UI CSS..."
Invoke-WebRequest -Uri "https://code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css" -OutFile "static/css/jquery-ui.css" -Verbose

# Download jQuery UI JS
Write-Host "Downloading jQuery UI JS..."
Invoke-WebRequest -Uri "https://code.jquery.com/ui/1.12.1/jquery-ui.min.js" -OutFile "static/js/jquery-ui.min.js" -Verbose

# Download Bootstrap Icons CSS
Write-Host "Downloading Bootstrap Icons CSS..."
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" -OutFile "static/css/bootstrap-icons.css" -Verbose

# Download Bootstrap Icons Font Files
Write-Host "Downloading Bootstrap Icons Font Files..."
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/fonts/bootstrap-icons.woff" -OutFile "static/fonts/bootstrap-icons.woff" -Verbose
Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/fonts/bootstrap-icons.woff2" -OutFile "static/fonts/bootstrap-icons.woff2" -Verbose

Write-Host "Verifying downloaded files..."
Get-ChildItem -Path "static" -Recurse | Select-Object FullName

Write-Host "All dependencies have been downloaded successfully!" 