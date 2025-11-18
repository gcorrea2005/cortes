from flask import Flask, request, render_template, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os
import json  # Importar json
from config import Config
from modules.core import leer_longitudes_todas, usar_piezas_inventario, cortar_barras_optimizadas, mostrar_plan_de_armado, procesar_piezas_para_corte_optimizado
from modules.inventory import leer_inventario
from modules.graphics import graficar_barras_estandar, graficar_plan_de_armado  # <-- Importar graficar_plan_de_armado
from modules.excel_export import exportar_a_excel

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)
    return app

app = create_app()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Subir archivo de Tekla
        tekla_file = request.files.get('tekla_file')
        # Subir archivo de inventario
        inventario_file = request.files.get('inventario_file')

        if not tekla_file or tekla_file.filename == '':
            flash('No seleccionaste archivo de Tekla.')
            return redirect(request.url)

        filename = secure_filename(tekla_file.filename)
        tekla_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        tekla_file.save(tekla_path)

        # Leer longitudes
        try:
            print("DEBUG: Leyendo archivo...")  # Log
            perfiles = leer_longitudes_todas(tekla_path)
            print(f"DEBUG: Perfiles leídos: {perfiles}")  # Log
        except Exception as e:
            print(f"DEBUG: Error al leer archivo: {e}")  # Log
            flash(f"Error al leer archivo: {e}")
            return redirect(url_for('index'))

        # Leer inventario si se subió
        inventario = {}
        if inventario_file and inventario_file.filename != '':
            filename_inv = secure_filename(inventario_file.filename)
            inventario_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_inv)
            inventario_file.save(inventario_path)

            inventario = leer_inventario(inventario_path)

        # === Ordenar perfiles por longitud total (de mayor a menor) ===
        print("DEBUG: Ordenando perfiles...")  # Log
        perfiles_ordenados = sorted(perfiles.items(), key=lambda x: sum(x[1]), reverse=True)
        print(f"DEBUG: Perfiles ordenados: {[p[0] for p in perfiles_ordenados]}")  # Log

        # === Procesar cada perfil y guardar como archivo JSON ===
        print("DEBUG: Iniciando procesamiento...")  # Log
        for perfil, lista_piezas in perfiles_ordenados:  # <-- Aquí está la variable definida
            print(f"DEBUG: Procesando perfil {perfil} con piezas: {lista_piezas}")  # Log

            piezas_disponibles = inventario.get(perfil, [])
            piezas_usadas, lista_piezas_restantes, _ = usar_piezas_inventario(lista_piezas, piezas_disponibles)

            print(f"DEBUG: Piezas usadas: {piezas_usadas}, Restantes: {lista_piezas_restantes}")  # Log

            # === Procesar piezas restantes para corte (devuelve barras Y partes) ===
            barras, partes = procesar_piezas_para_corte_optimizado(lista_piezas_restantes, limite_division=5995, longitud_barra=12000, cuchilla_corte=3)

            # === Cortar barras (ahora partes está en formato correcto) ===
            print(f"DEBUG: Cortando barras para perfil {perfil}...")  # Log
            barras = cortar_barras_optimizadas(12000, partes, cuchilla_corte=3)
            print(f"DEBUG: Barras generadas: {barras}")  # Log

            # === Generar plan de armado ===
            plan_armado = mostrar_plan_de_armado(partes, perfil, piezas_usadas)
            print(f"DEBUG: Plan de armado generado: {plan_armado}")  # Log

            # === Generar gráfico de corte ===
            grafico_corte = graficar_barras_estandar(barras, perfil, piezas_usadas, app.config['STATIC_FOLDER_IMAGES'])
            print(f"DEBUG: Gráfico de corte generado: {grafico_corte}")  # Log

            # === Generar gráfico de armado ===
            grafico_armado = graficar_plan_de_armado(plan_armado, perfil, app.config['STATIC_FOLDER_IMAGES'])  # <-- Agregar esta línea
            print(f"DEBUG: Gráfico de armado generado: {grafico_armado}")  # Log

            # === Exportar a Excel ===
            excel = exportar_a_excel({
                'barras': barras,
                'penalizacion_partes_chicas': 0  # Placeholder
            }, perfil, plan_armado, {}, piezas_usadas, app.config['OUTPUT_FOLDER'], grafico_corte, grafico_armado)  # <-- Agregar grafico_armado aquí

            # === Sanitizar el nombre del perfil para usarlo en el nombre del archivo ===
            nombre_perfil_sanitizado = "".join(c for c in perfil if c.isalnum() or c in " _-")

            # === Guardar resultado como archivo JSON ===
            resultado = {
                'perfil': perfil,
                'datos_tekla': {
                    'piezas_originales': lista_piezas,
                    'cantidad_total': len(lista_piezas),
                    'longitud_total': sum(lista_piezas)
                },
                'barras': barras,
                'partes': partes,
                'piezas_usadas': piezas_usadas,
                'plan_armado': plan_armado,
                'grafico_corte': grafico_corte,
                'grafico_armado': grafico_armado,  # <-- Agregar grafico_armado aquí
                'excel': excel
            }
            with open(os.path.join(app.config['OUTPUT_FOLDER'], f"resultado_{nombre_perfil_sanitizado}.json"), 'w') as f:
                json.dump(resultado, f)

        print("DEBUG: Procesamiento de todos los perfiles completado")  # Log
        print("DEBUG: Redirigiendo a seleccionar_perfil...")  # Log
        return redirect(url_for('seleccionar_perfil'))

    return render_template('upload.html')

@app.route('/seleccionar_perfil')
def seleccionar_perfil():
    print("DEBUG: Entrando a seleccionar_perfil")  # Log
    # === Leer archivos JSON de resultados ===
    resultados = []
    for filename in os.listdir(app.config['OUTPUT_FOLDER']):
        if filename.startswith("resultado_") and filename.endswith(".json"):
            with open(os.path.join(app.config['OUTPUT_FOLDER'], filename), 'r') as f:
                resultado = json.load(f)
            resultados.append(resultado)

    perfiles = [r['perfil'] for r in resultados]
    print(f"DEBUG: Perfiles encontrados: {perfiles}")  # Log
    return render_template('select_profile.html', perfiles=perfiles)

@app.route('/ver_resultado/<perfil_seleccionado>')
def ver_resultado(perfil_seleccionado):
    print(f"DEBUG: Entrando a ver_resultado para {perfil_seleccionado}")  # Log
    # === Sanitizar el nombre del perfil para usarlo en el nombre del archivo ===
    nombre_perfil_sanitizado = "".join(c for c in perfil_seleccionado if c.isalnum() or c in " _-")

    # === Leer archivo JSON de resultado ===
    resultado_path = os.path.join(app.config['OUTPUT_FOLDER'], f"resultado_{nombre_perfil_sanitizado}.json")
    if not os.path.exists(resultado_path):
        print(f"DEBUG: No se encontró resultado para {perfil_seleccionado}")  # Log
        flash(f"No se encontró resultado para el perfil: {perfil_seleccionado}")
        return redirect(url_for('seleccionar_perfil'))

    with open(resultado_path, 'r') as f:
        resultado_completo = json.load(f)

    print(f"DEBUG: Resultado encontrado para {perfil_seleccionado}")  # Log
    return render_template('single_result.html', resultado=resultado_completo)

@app.route('/download/<filename>')
def download_file(filename):
    print(f"DEBUG: Descargando archivo {filename}")  # Log
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    app.secret_key = 'tu_clave_secreta_aqui'  # Añadir clave secreta para sesiones
    app.run(debug=True)