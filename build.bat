@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set ROOT=%~dp0

echo ============================================
echo  Service-Tool - Build
echo ============================================
echo.

where py >nul 2>nul
if not errorlevel 1 ( set PYTHON=py & goto python_ok )
where python >nul 2>nul
if not errorlevel 1 ( set PYTHON=python & goto python_ok )
echo [FEHLER] Python wurde nicht gefunden.
pause & exit /b 1
:python_ok

%PYTHON% -m pyinstaller --version >nul 2>nul
if errorlevel 1 (
    echo [INFO] PyInstaller wird installiert...
    %PYTHON% -m pip install --upgrade pyinstaller
    if errorlevel 1 ( echo [FEHLER] PyInstaller konnte nicht installiert werden. & pause & exit /b 1 )
)

%PYTHON% -m pip show PyQt6 >nul 2>nul
if errorlevel 1 ( echo [INFO] PyQt6 wird installiert... & %PYTHON% -m pip install --upgrade PyQt6 )

echo.
echo [1/4] Alte Build-Artefakte aufraeumen...
if exist "build" rd /s /q "build"
if exist "dist\Service Tool.exe" del /q "dist\Service Tool.exe"

echo.
echo [2/4] Baue die EXE (das kann einige Minuten dauern)...
%PYTHON% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --splash "%ROOT%icons\icon.png" ^
    --name "Service Tool" ^
    --icon "%ROOT%icons\icon.ico" ^
    --add-data "%ROOT%icons\icon.ico;." ^
    --add-data "%ROOT%icons\icon.png;." ^
    --add-data "%ROOT%icons;icons" ^
    --distpath "%ROOT%dist" ^
    --workpath "%ROOT%build" ^
    --specpath "%ROOT%build" ^
    "%ROOT%main.py"

if errorlevel 1 ( echo. & echo [FEHLER] PyInstaller-Build fehlgeschlagen. & pause & exit /b 1 )

echo.
echo [3/4] Ressourcen neben die EXE kopieren...
if not exist "dist\res" mkdir "dist\res"
xcopy "res\templates" "dist\res\templates" /E /I /Y /Q >nul 2>nul
xcopy "res\kw_data" "dist\res\kw_data" /E /I /Y /Q >nul 2>nul
xcopy "res\et" "dist\res\et" /E /I /Y /Q >nul 2>nul
xcopy "res\fd" "dist\res\fd" /E /I /Y /Q >nul 2>nul

echo.
echo [4/4] Aufraeumen...
if exist "build" rd /s /q "build"

echo.
echo ============================================
echo  Build abgeschlossen!
echo  Die EXE liegt in:  dist\Service Tool.exe
echo ============================================
echo.
pause
endlocal
