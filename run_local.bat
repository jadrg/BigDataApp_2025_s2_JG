@echo off
title BigDataApp - Servidor Local PRO

REM ================================
REM COLORES (Windows)
REM ================================
REM 0 = Negro   1= Azul  2= Verde  3= Aqua  4= Rojo  5= Purpura
REM 6 = Amarillo 7 = Blanco  8 = Gris  9 = Azul Claro
color 0A

:MENU
cls
echo ==========================================
echo         BIGDATA APP - EJECUCION LOCAL
echo ==========================================
echo.
echo  [1] Iniciar servidor con AUTORELOAD
echo  [2] Iniciar servidor normal
echo  [3] Abrir navegador
echo  [4] Salir
echo.
set /p opc=Selecciona una opcion: 

if "%opc%"=="1" goto AUTORELOAD
if "%opc%"=="2" goto NORMAL
if "%opc%"=="3" start http://127.0.0.1:5000 & goto MENU
if "%opc%"=="4" exit
goto MENU

:AUTORELOAD
cls
echo ================================
echo  MODO AUTORELOAD 🚀
echo ================================
echo.

echo Activando entorno virtual...
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo ERROR: No se pudo activar venv.
    pause
    goto MENU
)

echo Entorno virtual activado ✓
echo.

echo Iniciando Flask con autoreload...
echo (cada cambio en archivos reiniciara el servidor)
echo.

start http://127.0.0.1:5000

python -m flask --app app --debug run --reload
pause
goto MENU


:NORMAL
cls
echo ================================
echo  MODO NORMAL ⚙️
echo ================================
echo.

echo Activando entorno virtual...
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo ERROR: No se pudo activar venv.
    pause
    goto MENU
)

echo Entorno virtual activado ✓
echo.

echo Iniciando servidor normal...
start http://127.0.0.1:5000
python app.py

pause
goto MENU