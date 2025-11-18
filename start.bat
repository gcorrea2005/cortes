@echo off
cd /d "%~dp0"

echo Activando entorno virtual...
call venv\Scripts\activate

echo Verificando e instalando dependencias...
pip install -r requirements.txt --quiet

echo Iniciando la aplicación Flask...
python app.py

pause