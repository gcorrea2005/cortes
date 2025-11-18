import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import os
import pandas as pd
from itertools import combinations
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

def leer_inventario(ruta_inventario):
    """
    Lee un archivo de inventario y devuelve un diccionario de piezas disponibles.
    Formato esperado: Perfil;Longitud;Cantidad;Ubicacion
    """
    inventario = {}
    if not os.path.exists(ruta_inventario):
        print(f"⚠️ Archivo de inventario no encontrado: {ruta_inventario}")
        return inventario

    try:
        with open(ruta_inventario, 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            encabezado = lineas[0].strip().split(';')
            for linea in lineas[1:]:
                partes = linea.strip().split(';')
                if len(partes) < 3:
                    continue
                perfil = partes[0].strip()
                longitud = int(partes[1].strip())
                cantidad = int(partes[2].strip())
                ubicacion = partes[3].strip() if len(partes) > 3 else "Desconocida"

                if perfil not in inventario:
                    inventario[perfil] = []
                inventario[perfil].extend([longitud] * cantidad)

    except Exception as e:
        print(f"❌ Error al leer inventario: {e}")

    return inventario


def usar_piezas_inventario(piezas_necesarias, inventario_perfil):
    """
    Intenta usar piezas del inventario para satisfacer las necesidades.
    Devuelve: (piezas_usadas, piezas_restantes, inventario_actualizado)
    """
    piezas_usadas = []
    piezas_restantes = piezas_necesarias[:]
    inventario_actualizado = inventario_perfil[:]

    for p in piezas_necesarias:
        if p in inventario_actualizado:
            inventario_actualizado.remove(p)
            piezas_usadas.append(p)
            piezas_restantes.remove(p)
            print(f"✅ Usando pieza del inventario: {p} mm")

    return piezas_usadas, piezas_restantes, inventario_actualizado


def generar_combinaciones_piezas(piezas, limite_division=5995, longitud_barra=12000, cuchilla_corte=3):
    """
    Genera todas las combinaciones posibles de piezas grandes completas vs divididas.
    """
    piezas_completas = []
    piezas_dividibles = []
    for i, p in enumerate(piezas):
        if p + cuchilla_corte <= longitud_barra:
            piezas_completas.append((i, p))
        else:
            piezas_dividibles.append((i, p))

    todas_las_combinaciones = []
    # Probar todas las combinaciones de piezas completas (0 piezas completas, 1 pieza completa, ..., todas completas)
    for r in range(len(piezas_completas) + 1):
        for comb in combinations(piezas_completas, r):
            combinacion = {
                'completas': list(comb),
                'divididas': [p for p in piezas_completas if p not in comb] + piezas_dividibles
            }
            todas_las_combinaciones.append(combinacion)

    return todas_las_combinaciones


def generar_cortes_optimos(pieza, porcentaje_min=0.10, porcentaje_max=0.30, limite_minimo=1000):
    """
    Genera todas las combinaciones posibles de cortes para una pieza,
    dentro del rango de porcentaje_min a porcentaje_max, y preferiblemente > limite_minimo.
    """
    cortes = []

    # Calcular rango de corte
    min_corte = max(int(pieza * porcentaje_min), limite_minimo)
    max_corte = int(pieza * porcentaje_max)

    # Generar todos los cortes posibles
    for corte1 in range(min_corte, max_corte + 1):
        corte2 = pieza - corte1
        if corte2 >= corte1:  # Evitar duplicados
            cortes.append((corte1, corte2))

    return cortes


def cortar_barras_optimizadas(longitud_barra, partes, cuchilla_corte=3):
    """
    Algoritmo First Fit Decreasing para cortar barras, considerando cuchilla de corte.
    """
    longitudes = [p[1] + cuchilla_corte for p in partes]

    for p in longitudes:
        if p > longitud_barra:
            raise ValueError(f"La parte de {p - cuchilla_corte}mm (con corte: {p}mm) no cabe en una barra de {longitud_barra}mm")

    partes_ordenadas = sorted(zip(partes, longitudes), key=lambda x: x[1], reverse=True)
    partes_nombres = [x[0] for x in partes_ordenadas]
    partes_longitudes = [x[1] for x in partes_ordenadas]

    barras = []

    for nombre_parte, longitud_parte in zip(partes_nombres, partes_longitudes):
        asignada = False
        for barra in barras:
            if barra['resto'] >= longitud_parte:
                barra['partes'].append((nombre_parte, longitud_parte))
                barra['resto'] -= longitud_parte
                asignada = True
                break

        if not asignada:
            nueva_barra = {
                'id': f"BAR-{len(barras) + 1:03d}",
                'partes': [(nombre_parte, longitud_parte)],
                'resto': longitud_barra - longitud_parte
            }
            barras.append(nueva_barra)

    return barras


def evaluar_partes_chicas(partes, limite_minimo=1000, porcentaje_min=0.10, porcentaje_max=0.30):
    """
    Evalúa si alguna parte chica (< limite_minimo) no cumple con el porcentaje_min y porcentaje_max.
    Devuelve el número de partes que no cumplen (penalización).
    """
    penalizacion = 0

    # Agrupar partes por pieza original (índice)
    piezas_grupos = {}
    for nombre, longitud in partes:
        pieza_num = int(nombre[:-1])  # Extraer el número de la pieza (1, 2, 3, ...)
        if pieza_num not in piezas_grupos:
            piezas_grupos[pieza_num] = []
        piezas_grupos[pieza_num].append((nombre, longitud))

    for pieza_num, partes_pieza in piezas_grupos.items():
        if len(partes_pieza) > 1:  # Solo si se dividió la pieza
            longitudes = [l for _, l in partes_pieza]
            longitud_total = sum(longitudes)
            partes_chicas = [p for p in partes_pieza if p[1] < limite_minimo]
            if partes_chicas:
                for nombre, longitud in partes_chicas:
                    porcentaje = (longitud / longitud_total) * 100
                    if not (porcentaje_min <= porcentaje <= porcentaje_max):
                        penalizacion += 1  # Penalizar por cada parte que no cumple

    return penalizacion


def probar_combinaciones_doble_optimizacion_con_partes_chicas(piezas, limite_division=5995, longitud_barra=12000, cuchilla_corte=3):
    """
    Prueba todas las combinaciones posibles y devuelve la mejor según:
    1. Menor número de barras.
    2. Mayor número de piezas completas sin cortar.
    3. Menor penalización por partes chicas que no cumplen con el criterio.
    """
    combinaciones = generar_combinaciones_piezas(piezas, limite_division, longitud_barra, cuchilla_corte)
    mejor_resultado = None
    mejor_puntaje = float('inf')  # Menor número de barras, mayor piezas completas, menor penalización

    for comb in combinaciones:
        partes = []
        idx_parte = 1

        # Piezas completas
        for i, p in comb['completas']:
            partes.append((f"{idx_parte}a", p))
            idx_parte += 1

        # Piezas divididas
        for i, p in comb['divididas']:
            if p > limite_division:
                # === Aplicar criterio solo a piezas entre 6000 y 7000 mm ===
                if 6000 <= p <= 7000:
                    cortes_posibles = generar_cortes_optimos(p, porcentaje_min=0.10, porcentaje_max=0.30, limite_minimo=1000)
                    if cortes_posibles:
                        # Tomar el primer corte (podría optimizarse más)
                        corte1, corte2 = cortes_posibles[0]
                        partes.append((f"{idx_parte}a", corte1))
                        partes.append((f"{idx_parte}b", corte2))
                        idx_parte += 1
                    else:
                        # Si no hay cortes válidos, usar división simple
                        restante = p
                        parte_letra = 'a'
                        while restante > 0:
                            if restante > limite_division:
                                partes.append((f"{idx_parte}{parte_letra}", limite_division))
                                restante -= limite_division
                            else:
                                partes.append((f"{idx_parte}{parte_letra}", restante))
                                restante = 0
                            parte_letra = chr(ord(parte_letra) + 1)
                        idx_parte += 1
                else:
                    # Para piezas > 7000, usar división simple
                    restante = p
                    parte_letra = 'a'
                    while restante > 0:
                        if restante > limite_division:
                            partes.append((f"{idx_parte}{parte_letra}", limite_division))
                            restante -= limite_division
                        else:
                            partes.append((f"{idx_parte}{parte_letra}", restante))
                            restante = 0
                        parte_letra = chr(ord(parte_letra) + 1)
                    idx_parte += 1
            else:
                partes.append((f"{idx_parte}a", p))
                idx_parte += 1

        # Cortar barras
        resultado = cortar_barras_optimizadas(longitud_barra, partes, cuchilla_corte)

        # Calcular penalización por partes chicas
        penalizacion_partes_chicas = evaluar_partes_chicas(partes, limite_minimo=1000, porcentaje_min=0.10, porcentaje_max=0.30)

        # Calcular puntaje: barras * 1000000 - piezas_completas * 1000 + penalizacion_partes_chicas
        # Prioridad: barras > piezas_completas > penalización_partes_chicas
        barras = len(resultado)
        piezas_completas = len(comb['completas'])
        puntaje = barras * 1000000 - piezas_completas * 1000 + penalizacion_partes_chicas

        if puntaje < mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_resultado = {
                'barras': resultado,
                'partes': partes,
                'combinacion': comb,
                'penalizacion_partes_chicas': penalizacion_partes_chicas
            }

    return mejor_resultado


def mostrar_plan_de_armado(partes, perfil, piezas_usadas_inventario):
    """
    Muestra cómo ensamblar cada pieza original usando sus partes.
    Incluye piezas usadas del inventario como piezas completas.
    """
    print(f"\n" + "="*60)
    print(f"PLAN DE ARMADO PARA {perfil}:")
    print("="*60)

    # Agrupar partes por pieza original (índice)
    piezas_grupos = {}
    idx = 1
    for nombre, longitud in partes:
        pieza_num = int(nombre[:-1])  # Extraer el número de la pieza (1, 2, 3, ...)
        if pieza_num not in piezas_grupos:
            piezas_grupos[pieza_num] = []
        piezas_grupos[pieza_num].append((nombre, longitud))

    # Agrupar piezas usadas del inventario
    for longitud in piezas_usadas_inventario:
        piezas_grupos[idx] = [(f"{idx}a", longitud)]
        idx += 1

    # Mostrar plan de armado
    for pieza_num in sorted(piezas_grupos.keys()):
        partes_pieza = piezas_grupos[pieza_num]
        if len(partes_pieza) == 1:
            nombre, longitud = partes_pieza[0]
            print(f"Pieza-{pieza_num}: {nombre}({longitud})")
        else:
            partes_str = [f"{nombre}({longitud})" for nombre, longitud in partes_pieza]
            print(f"Pieza-{pieza_num}: {' + '.join(partes_str)} → Ensamblar en una sola pieza")

    return piezas_grupos


def graficar_plan_de_armado(partes, perfil, piezas_usadas_inventario):
    """
    Grafica cómo ensamblar cada pieza original usando sus partes.
    Incluye piezas usadas del inventario como piezas completas.
    """
    print(f"\n📊 Mostrando plan de armado gráfico para {perfil}...")

    # Agrupar partes por pieza original (índice)
    piezas_grupos = {}
    idx = 1
    for nombre, longitud in partes:
        pieza_num = int(nombre[:-1])  # Extraer el número de la pieza (1, 2, 3, ...)
        if pieza_num not in piezas_grupos:
            piezas_grupos[pieza_num] = []
        piezas_grupos[pieza_num].append((nombre, longitud))

    # Agrupar piezas usadas del inventario
    for longitud in piezas_usadas_inventario:
        piezas_grupos[idx] = [(f"{idx}a", longitud)]
        idx += 1

    # Ordenar piezas por índice
    piezas_ordenadas = sorted(piezas_grupos.items())

    # Calcular tamaño del gráfico
    num_piezas = len(piezas_ordenadas)
    if num_piezas == 0:
        print(f"No hay piezas para graficar en {perfil}.")
        return

    fig, ax = plt.subplots(figsize=(14, max(4, num_piezas * 0.6)))

    # Generar colores
    colores = []
    for _ in range(100):
        r = random.uniform(0.3, 0.85)
        g = random.uniform(0.3, 0.85)
        b = random.uniform(0.3, 0.85)
        colores.append((r, g, b))

    for i, (pieza_num, partes_pieza) in enumerate(piezas_ordenadas):
        y_pos = num_piezas - i
        x_start = 0.0

        # Dibujar partes de la pieza
        for j, (nombre, longitud) in enumerate(partes_pieza):
            color = colores[j % len(colores)]
            rect = patches.Rectangle(
                (x_start / 1000, y_pos - 0.4), longitud / 1000, 0.8,
                linewidth=1, edgecolor='black', facecolor=color
            )
            ax.add_patch(rect)
            etiqueta = f"{nombre}({longitud})"
            ax.text(
                x_start / 1000 + longitud / 2000, y_pos, etiqueta,
                va='center', ha='center', fontsize=9,
                color='white', weight='bold'
            )
            x_start += longitud

        # Etiqueta de la pieza (arriba)
        ax.text(-0.5, y_pos, f"Pieza-{pieza_num}", va='center', ha='right', fontsize=10, weight='bold')

    ax.set_xlim(0, max(12.5, x_start / 1000 + 0.5))
    ax.set_ylim(0, num_piezas + 1)
    ax.set_xlabel("Longitud (metros)", fontsize=12)
    ax.set_title(f"Plan de Armado - {perfil}", fontsize=14)
    ax.set_yticks([])
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.show()


def mostrar_resultado_como_tabla(partes, perfil, piezas_usadas_inventario):
    """
    Muestra el resultado en formato tabla como esperas.
    Incluye piezas usadas del inventario como piezas completas.
    """
    print(f"\n" + "="*60)
    print(f"RESULTADO PARA {perfil}:")
    print("="*60)

    # Agrupar partes por pieza original (índice)
    piezas_grupos = {}
    idx = 1
    for nombre, longitud in partes:
        pieza_num = int(nombre[:-1])  # Extraer el número de la pieza (1, 2, 3, ...)
        if pieza_num not in piezas_grupos:
            piezas_grupos[pieza_num] = []
        piezas_grupos[pieza_num].append((nombre, longitud))

    # Agrupar piezas usadas del inventario
    for longitud in piezas_usadas_inventario:
        piezas_grupos[idx] = [(f"{idx}a", longitud)]
        idx += 1

    # Mostrar tabla
    for pieza_num in sorted(piezas_grupos.keys()):
        etiquetas = [f"{nombre}({longitud})" for nombre, longitud in piezas_grupos[pieza_num]]
        print(f"Pieza-{pieza_num}\t" + "\t".join(etiquetas))

    return piezas_grupos


def graficar_barras_estandar(barras, perfil, piezas_usadas_inventario):
    """
    Grafica barras estándar de 12000 mm con piezas y desperdicio.
    Incluye piezas usadas del inventario como barras virtuales.
    """
    # === Generar barras virtuales para piezas del inventario ===
    barras_inventario = []
    for i, longitud in enumerate(piezas_usadas_inventario):
        barras_inventario.append({
            'id': f"BAR-{i + 1:03d}",  # Rotulado como BAR-001, etc.
            'partes': [(f"INV-{i+1:03d}", longitud)],  # Rotulado como INV-01(6000), etc.
            'resto': 0  # Sin desperdicio
        })

    # === Combinar barras de inventario y nuevas ===
    todas_las_barras = barras_inventario + barras  # Prioridad al inventario
    num_barras = len(todas_las_barras)

    if num_barras == 0:
        print(f"No hay barras que graficar para {perfil}.")
        return

    fig, ax = plt.subplots(figsize=(14, max(4, num_barras * 0.6)))
    
    colores = []
    for _ in range(100):
        r = random.uniform(0.3, 0.85)
        g = random.uniform(0.3, 0.85)
        b = random.uniform(0.3, 0.85)
        colores.append((r, g, b))

    for i, barra in enumerate(todas_las_barras):
        y_pos = num_barras - i
        x_start = 0.0

        # Dibujar partes
        for j, (nombre_parte, longitud_parte) in enumerate(barra['partes']):
            color = colores[j % len(colores)]
            rect = patches.Rectangle(
                (x_start / 1000, y_pos - 0.4), longitud_parte / 1000, 0.8,  # Convertir a metros
                linewidth=1, edgecolor='black', facecolor=color
            )
            ax.add_patch(rect)
            # === Etiqueta: INV-01(6000) o 1a(887) ===
            etiqueta = f"{nombre_parte}({longitud_parte})"
            ax.text(
                x_start / 1000 + longitud_parte / 2000, y_pos, etiqueta,
                va='center', ha='center', fontsize=9,
                color='white', weight='bold'
            )
            x_start += longitud_parte

        # Dibujar desperdicio
        if barra['resto'] > 0.01:
            rect_waste = patches.Rectangle(
                (x_start / 1000, y_pos - 0.4), barra['resto'] / 1000, 0.8,
                linewidth=1, edgecolor='black', facecolor='lightgray'
            )
            ax.add_patch(rect_waste)
            ax.text(
                (x_start + barra['resto'] / 2) / 1000, y_pos, f"Desp\n{barra['resto']:.0f}",
                va='center', ha='center', fontsize=8, color='black'
            )

        # Etiqueta de la barra (arriba)
        ax.text(-0.5, y_pos, f"{barra['id']}", va='center', ha='right', fontsize=10, weight='bold')

    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, num_barras + 1)
    ax.set_xlabel("Longitud (metros)", fontsize=12)
    ax.set_title(f"Plan de Corte - {perfil} - Barras usadas", fontsize=14)
    ax.set_yticks([])
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.show()


def leer_longitudes_todas(ruta_archivo):
    """
    Lee un archivo de lista de materiales de Tekla y devuelve un diccionario
    con cada perfil y sus longitudes (respetando cantidad).
    """
    perfiles = {}

    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_archivo}")

    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or "Sub total" in linea or "Total:" in linea or "Profile" in linea:
                continue

            partes = linea.split(';')
            if len(partes) < 4:
                continue

            perfil = partes[0].strip()
            if not perfil:
                continue

            try:
                cantidad = int(partes[2].strip())
                longitud_mm = int(partes[3].strip())
                if perfil not in perfiles:
                    perfiles[perfil] = []
                perfiles[perfil].extend([longitud_mm] * cantidad)
            except (ValueError, IndexError):
                continue

    return perfiles


def exportar_a_excel(mejor, perfil, piezas_armado, piezas_resultado, piezas_usadas_inventario):
    """
    Exporta los resultados a un archivo Excel con múltiples hojas.
    """
    # Sanitizar el nombre del perfil para usarlo en el nombre del archivo
    nombre_perfil_sanitizado = "".join(c for c in perfil if c.isalnum() or c in " _-")
    nombre_archivo = f"Reporte_Corte_{nombre_perfil_sanitizado}.xlsx"

    # Crear libro de Excel
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Resumen"

    # === Hoja 1: Resumen ===
    ws1.append(["Perfil", perfil])
    ws1.append(["Total de barras usadas", len(mejor['barras'])])
    ws1.append(["Piezas usadas del inventario", len(piezas_usadas_inventario)])
    ws1.append(["Penalización por partes chicas", mejor['penalizacion_partes_chicas']])
    ws1.append([""])

    # === Hoja 2: Plan de Corte ===
    ws2 = wb.create_sheet(title="Plan de Corte")
    ws2.append(["ID Barra", "Partes", "Desperdicio (mm)"])
    # === Agregar barras de inventario ===
    for i, longitud in enumerate(piezas_usadas_inventario):
        id_barra = f"BAR-{i + 1:03d}"
        ws2.append([id_barra, f"INV-{i+1:03d}({longitud})", 0])
    # === Agregar barras nuevas ===
    for barra in mejor['barras']:
        partes_str = [f"{p[0]}({p[1]})" for p in barra['partes']]  # Convertir tuplas a strings
        ws2.append([barra['id'], ", ".join(partes_str), barra['resto']])

    # === Hoja 3: Piezas del Inventario Usadas ===
    ws3 = wb.create_sheet(title="Inventario Usado")
    ws3.append(["Pieza", "Longitud (mm)"])
    for p in piezas_usadas_inventario:
        ws3.append(["Inventario", p])

    # === Hoja 4: Plan de Armado ===
    ws4 = wb.create_sheet(title="Plan de Armado")
    ws4.append(["Pieza", "Partes"])
    for pieza_num in sorted(piezas_armado.keys()):
        partes_pieza = piezas_armado[pieza_num]
        if len(partes_pieza) == 1:
            nombre, longitud = partes_pieza[0]
            ws4.append([f"Pieza-{pieza_num}", f"{nombre}({longitud})"])
        else:
            partes_str = [f"{nombre}({longitud})" for nombre, longitud in partes_pieza]
            ws4.append([f"Pieza-{pieza_num}", " + ".join(partes_str)])

    # === Hoja 5: Resultado Tabla ===
    ws5 = wb.create_sheet(title="Resultado Tabla")
    ws5.append(["Pieza", "Partes"])
    for pieza_num in sorted(piezas_resultado.keys()):
        etiquetas = [f"{nombre}({longitud})" for nombre, longitud in piezas_resultado[pieza_num]]
        ws5.append([f"Pieza-{pieza_num}", "\t".join(etiquetas)])

    # Guardar archivo
    wb.save(nombre_archivo)
    print(f"\n✅ Reporte exportado a: {nombre_archivo}")


# === CONFIGURACIÓN DEL USUARIO ===
if __name__ == "__main__":
    # Ruta al archivo de Tekla
    ruta = "material_list.txt"  # Cambia por tu archivo real
    # Ruta al archivo de inventario
    ruta_inventario = "inventario.txt"  # Cambia por tu archivo real

    # Leer inventario
    inventario = leer_inventario(ruta_inventario)
    print(f"✅ Inventario leído: {inventario}")

    # Leer todos los perfiles
    try:
        todos_los_perfiles = leer_longitudes_todas(ruta)
        print(f"✅ Se leyeron {len(todos_los_perfiles)} perfiles distintos.")
    except Exception as e:
        print("❌ Error al leer archivo:", e)
        exit(1)

    # Longitud de la barra estándar (en mm)
    L = 12000  # mm
    CUCHILLA_CORTE = 3  # mm

    # Procesar cada perfil
    for perfil, lista_piezas in todos_los_perfiles.items():
        print(f"\n" + "="*60)
        print(f"Procesando perfil: {perfil}")
        print(f"Piezas originales: {lista_piezas}")

        # === Verificar inventario para este perfil ===
        piezas_disponibles = inventario.get(perfil, [])
        print(f"Piezas disponibles en inventario: {piezas_disponibles}")

        # === Usar piezas del inventario ===
        piezas_usadas, lista_piezas_restantes, inventario[perfil] = usar_piezas_inventario(lista_piezas, piezas_disponibles)

        print(f"Piezas usadas del inventario: {piezas_usadas}")
        print(f"Piezas restantes por cortar: {lista_piezas_restantes}")
        print(f"Inventario restante para {perfil}: {inventario[perfil]}")

        # === Paso 1: Probar todas las combinaciones posibles con triple optimización ===
        if lista_piezas_restantes:
            mejor = probar_combinaciones_doble_optimizacion_con_partes_chicas(
                lista_piezas_restantes, limite_division=5995, longitud_barra=L, cuchilla_corte=CUCHILLA_CORTE
            )
        else:
            mejor = {
                'barras': [],
                'partes': [],
                'combinacion': {'completas': [], 'divididas': []},
                'penalizacion_partes_chicas': 0
            }

        print(f"\n✅ Mejor combinación encontrada:")
        print(f"Total de barras usadas: {len(mejor['barras'])}")
        print(f"Penalización por partes chicas: {mejor['penalizacion_partes_chicas']}")
        print("Partes generadas:", mejor['partes'])

        # Mostrar en consola
        print("\nDetalle de barras:")
        for barra in mejor['barras']:
            partes_names = [p[0] for p in barra['partes']]
            print(f"  {barra['id']}: {partes_names} → Desperdicio: {barra['resto']:.0f} mm")

        # === Mostrar resultado en formato tabla ===
        piezas_resultado = mostrar_resultado_como_tabla(mejor['partes'], perfil, piezas_usadas)

        # === Mostrar plan de armado ===
        piezas_armado = mostrar_plan_de_armado(mejor['partes'], perfil, piezas_usadas)

        # === Exportar a Excel ===
        exportar_a_excel(mejor, perfil, piezas_armado, piezas_resultado, piezas_usadas)

        # === Mostrar plan de armado gráfico ===
        graficar_plan_de_armado(mejor['partes'], perfil, piezas_usadas)

        # Mostrar gráfico de corte
        graficar_barras_estandar(mejor['barras'], perfil, piezas_usadas)