@echo off
title SonaPrism Setup
echo ============================================
echo         SonaPrism - Automated Setup
echo ============================================
echo.
echo This will download and install:
echo   1. Equalizer APO (system audio processor)
echo   2. LoudMax (limiter plugin)
echo   3. ReaPlugs (effects plugins)
echo.
echo You will need to RESTART your computer after.
echo.
pause

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Please right-click this file and select
    echo "Run as administrator" then try again.
    echo.
    pause
    exit /b 1
)

:: Create temp download folder
set "DLDIR=%TEMP%\SonaPrism_Setup"
mkdir "%DLDIR%" 2>nul

echo.
echo [1/3] Downloading Equalizer APO...
powershell -Command "Invoke-WebRequest -Uri 'https://sourceforge.net/projects/equalizerapo/files/latest/download' -OutFile '%DLDIR%\EqualizerAPO_Setup.exe' -UserAgent 'Mozilla/5.0'"
if not exist "%DLDIR%\EqualizerAPO_Setup.exe" (
    echo FAILED to download Equalizer APO.
    echo Please download manually from: https://sourceforge.net/projects/equalizerapo/
    pause
    exit /b 1
)
echo Done.

echo.
echo [2/3] Downloading ReaPlugs...
powershell -Command "Invoke-WebRequest -Uri 'https://www.reaper.fm/reaplugs/reaplugs236_x64-install.exe' -OutFile '%DLDIR%\reaplugs_setup.exe' -UserAgent 'Mozilla/5.0'"
if not exist "%DLDIR%\reaplugs_setup.exe" (
    echo FAILED to download ReaPlugs.
    echo Please download manually from: https://www.reaper.fm/reaplugs/
    pause
    exit /b 1
)
echo Done.

echo.
echo [3/3] Downloading LoudMax...
powershell -Command "Invoke-WebRequest -Uri 'https://loudmax.blogspot.com/' -OutFile '%DLDIR%\loudmax_page.html' -UserAgent 'Mozilla/5.0'"
echo NOTE: LoudMax must be downloaded manually (blogspot blocks direct downloads).
echo.

:: Install Equalizer APO
echo.
echo ============================================
echo Installing Equalizer APO...
echo   - Select your audio output device when asked
echo   - Complete the installer normally
echo ============================================
echo.
start /wait "%DLDIR%\EqualizerAPO_Setup.exe"

:: Create VSTPlugins folder
mkdir "C:\Program Files\EqualizerAPO\VSTPlugins" 2>nul

:: Install ReaPlugs
echo.
echo ============================================
echo Installing ReaPlugs...
echo   - Use the default install location
echo   - Complete the installer normally
echo ============================================
echo.
start /wait "%DLDIR%\reaplugs_setup.exe"

:: Copy ReaPlugs DLLs to Equalizer APO
echo.
echo Copying plugin files...
if exist "C:\Program Files\VSTPlugins\ReaPlugs\reacomp-standalone.dll" (
    copy "C:\Program Files\VSTPlugins\ReaPlugs\reacomp-standalone.dll" "C:\Program Files\EqualizerAPO\VSTPlugins\" >nul
    copy "C:\Program Files\VSTPlugins\ReaPlugs\readelay-standalone.dll" "C:\Program Files\EqualizerAPO\VSTPlugins\" >nul
    echo ReaPlugs copied successfully.
) else (
    echo Could not find ReaPlugs DLLs automatically.
    echo Please manually copy reacomp-standalone.dll and readelay-standalone.dll
    echo from the ReaPlugs install folder to:
    echo C:\Program Files\EqualizerAPO\VSTPlugins\
)

:: LoudMax instructions
echo.
echo ============================================
echo MANUAL STEP: Install LoudMax
echo ============================================
echo.
echo 1. Go to: https://loudmax.blogspot.com/
echo 2. Download the VST2 Windows 64-bit version
echo 3. Extract LoudMax64.dll to:
echo    C:\Program Files\EqualizerAPO\VSTPlugins\
echo.
echo Opening the LoudMax website for you...
start https://loudmax.blogspot.com/
echo.
pause

:: Copy SonaPrism.exe to Program Files
echo.
echo Installing SonaPrism...
mkdir "C:\Program Files\SonaPrism" 2>nul
copy "%~dp0SonaPrism.exe" "C:\Program Files\SonaPrism\SonaPrism.exe" >nul
echo SonaPrism installed to: C:\Program Files\SonaPrism\

:: Create desktop shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'SonaPrism.lnk')); $sc.TargetPath = 'C:\Program Files\SonaPrism\SonaPrism.exe'; $sc.Description = 'SonaPrism Audio EQ'; $sc.Save()"
echo Desktop shortcut created.

:: Cleanup
rmdir /s /q "%DLDIR%" 2>nul

echo.
echo ============================================
echo         Setup Complete!
echo ============================================
echo.
echo IMPORTANT: You must RESTART your computer
echo for Equalizer APO to start working.
echo.
echo After restart:
echo   - Make sure LoudMax64.dll is in the VSTPlugins folder
echo   - Run SonaPrism from your Desktop shortcut
echo     (right-click, Run as administrator)
echo.
choice /m "Restart now?"
if %errorlevel% equ 1 (
    shutdown /r /t 10 /c "Restarting for SonaPrism setup..."
)
