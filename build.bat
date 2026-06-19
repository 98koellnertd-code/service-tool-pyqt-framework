@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  Servicetechniker Tool - Build
echo ============================================
echo.

REM --- Python vorhanden? ---
where python >nul 2>nul
if errorlevel 1 (
    echo [FEHLER] Python wurde nicht gefunden. Bitte Python installieren und
    echo          zum PATH hinzufuegen.
    pause
    exit /b 1
)

REM --- PyInstaller vorhanden? Sonst installieren. ---
python -m pyinstaller --version >nul 2>nul
if errorlevel 1 (
    echo [INFO] PyInstaller wird installiert...
    python -m pip install --upgrade pyinstaller
    if errorlevel 1 (
        echo [FEHLER] PyInstaller konnte nicht installiert werden.
        pause
        exit /b 1
    )
)

REM --- PyQt6 vorhanden? Sonst installieren. ---
python -m pip show PyQt6 >nul 2>nul
if errorlevel 1 (
    echo [INFO] PyQt6 wird installiert...
    python -m pip install --upgrade PyQt6
)

echo.
echo [1/5] Alte Build-Artefakte aufraeumen...
if exist "build" rd /s /q "build"
if exist "TimingTool.spec" del /q "TimingTool.spec"
if exist "dist\TimingTool.exe" del /q "dist\TimingTool.exe"
if exist "dist\_internal" rd /s /q "dist\_internal"
if exist "dist\TimingTool" rd /s /q "dist\TimingTool"

echo.
echo [2/5] Baue die EXE mit PyInstaller (das kann einen Moment dauern)...
REM --onedir statt --onefile: Dateien bleiben dauerhaft entpackt liegen statt
REM sich bei JEDEM Start neu in einen zufaelligen Temp-Ordner zu entpacken.
REM Das vermeidet spuerbare Traegheit durch wiederholtes Antivirus-Rescannen
REM frisch erzeugter DLLs (bekanntes --onefile-Problem, v.a. auf Firmen-PCs
REM mit aktivem Echtzeitschutz).
python -m PyInstaller ^
    --onedir ^
    --windowed ^
    --name "TimingTool" ^
    --icon "%CD%\icon.ico" ^
    --add-data "%CD%\icon.ico;." ^
    --add-data "%CD%\icons;icons" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    main.py

if errorlevel 1 (
    echo.
    echo [FEHLER] PyInstaller-Build fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo [3/5] EXE und Bibliotheken aus dist\TimingTool nach dist verschieben...
REM PyInstaller legt bei --onedir alles in dist\TimingTool\ ab. Damit die
REM EXE wie gewuenscht direkt in dist\ liegt, eine Ebene nach oben verschieben.
move /Y "dist\TimingTool\TimingTool.exe" "dist\TimingTool.exe" >nul
move /Y "dist\TimingTool\_internal" "dist\_internal" >nul
rd /s /q "dist\TimingTool"

echo.
echo [4/5] Ressourcen nach dist kopieren...

REM icon.ico steckt bereits fest in der EXE (--add-data), muss NICHT separat
REM mitgeschickt werden (siehe utils.py: ICON_FILE -> MEIPASS_DIR).

REM Statische Daten aus res mit nach dist\res kopieren (Templates, Ersatzteile,
REM Fehlerdiagnose-Kataloge, KW-Daten). Laufzeit-Dateien wie user_profile.json
REM oder kunden_vorlagen.json werden bewusst NICHT mitkopiert, damit auf dem
REM Zielrechner keine Profile/Test-Daten ueberschrieben werden.
if not exist "dist\res" mkdir "dist\res"
xcopy "res\templates" "dist\res\templates" /E /I /Y /Q >nul 2>nul
xcopy "res\kw_data"   "dist\res\kw_data"   /E /I /Y /Q >nul 2>nul
xcopy "res\et"        "dist\res\et"        /E /I /Y /Q >nul 2>nul
xcopy "res\fd"        "dist\res\fd"        /E /I /Y /Q >nul 2>nul

echo.
echo [5/5] Aufraeumen...
if exist "build" rd /s /q "build"

echo.
echo ============================================
echo  Build abgeschlossen!
echo  Die EXE liegt in:  dist\TimingTool.exe
echo  (Daneben liegt der Ordner "_internal" mit den
echo   Bibliotheken - das ist normal, bitte mit
echo   weitergeben.)
echo  Zum Weitergeben einfach den gesamten Ordner
echo  "dist" kopieren (EXE + _internal + res).
echo ============================================
echo.
pause
endlocal
