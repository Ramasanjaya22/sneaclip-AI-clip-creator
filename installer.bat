@echo off
setlocal
set "PIP_NO_INDEX="

if /i "%HTTP_PROXY%"=="http://127.0.0.1:9" set "HTTP_PROXY="
if /i "%HTTPS_PROXY%"=="http://127.0.0.1:9" set "HTTPS_PROXY="
if /i "%ALL_PROXY%"=="http://127.0.0.1:9" set "ALL_PROXY="
if /i "%http_proxy%"=="http://127.0.0.1:9" set "http_proxy="
if /i "%https_proxy%"=="http://127.0.0.1:9" set "https_proxy="
if /i "%all_proxy%"=="http://127.0.0.1:9" set "all_proxy="

echo Installing application...
set "INSTALL_DIR=%~dp0miniconda"

if not exist "%INSTALL_DIR%" (
    echo Downloading Miniconda...
    curl -o "miniconda_installer.exe" "https://repo.anaconda.com/miniconda/Miniconda3-py39_25.7.0-2-Windows-x86_64.exe"

    echo Installing Miniconda...
    start /wait "" "miniconda_installer.exe" /S /RegisterPython=0 /AddToPath=0 /InstallationType=JustMe /D=%INSTALL_DIR%
    del "miniconda_installer.exe"
)

set "PYTHON_EXE=%INSTALL_DIR%\python.exe"
if not exist "%PYTHON_EXE%" (
    echo ERROR: Bundled Python not found at "%PYTHON_EXE%"
    pause
    exit /b 1
)

echo Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: pip upgrade failed with error code %ERRORLEVEL%!
    pause
    exit /b %ERRORLEVEL%
)

echo Installing PyTorch (optional)...
call "%PYTHON_EXE%" -m pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 (
    echo WARNING: Optional PyTorch install failed with error code %ERRORLEVEL%!
    echo WARNING: The app will run in fallback mode without the AI model.
)

echo Installing additional requirements...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Python dependencies installation failed with error code %ERRORLEVEL%!
    pause
    exit /b %ERRORLEVEL%
)

echo Installation complete!
pause
