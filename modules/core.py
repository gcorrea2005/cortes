def leer_longitudes_todas(ruta_archivo):
    """
    Lee un archivo de lista de materiales de Tekla y devuelve un diccionario
    con cada perfil y sus longitudes (respetando cantidad).
    """
    perfiles = {}

    with open(ruta_archivo, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            # === Ignorar líneas vacías o con Sub total, Total:, Profile ===
            if not linea or "Sub total" in linea or "Total:" in linea or "Profile" in linea:
                continue

            partes = linea.split(';')
            if len(partes) < 4:
                continue

            perfil = partes[0].strip()
            # === Limpiar caracteres raros del nombre del perfil ===
            perfil = "".join(c for c in perfil if c.isalnum() or c in " _-*")

            if not perfil:
                continue

            try:
                cantidad = int(partes[2].strip())
                # === Convertir longitud a entero (redondear si es decimal) ===
                longitud_raw = partes[3].strip()
                longitud_float = float(longitud_raw)
                longitud_int = int(round(longitud_float))
                if perfil not in perfiles:
                    perfiles[perfil] = []
                perfiles[perfil].extend([longitud_int] * cantidad)
            except (ValueError, IndexError):
                # === Ignorar filas con valores no numéricos ===
                continue

    return perfiles


def mostrar_datos_tekla(perfiles):
    """
    Muestra los datos leídos de Tekla Structures.
    """
    print("\n" + "="*60)
    print("DATOS LEÍDOS DE TEKLA STRUCTURES:")
    print("="*60)
    for perfil, lista_piezas in perfiles.items():
        print(f"\nPerfil: {perfil}")
        print(f"  Piezas: {lista_piezas}")
        print(f"  Cantidad total: {len(lista_piezas)}")
        # === Calcular longitud total correctamente ===
        longitud_total = sum(lista_piezas)
        print(f"  Longitud total: {longitud_total} mm")

    return perfiles


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
    Optimizado para minimizar desperdicio y número de barras.
    """
    # === Verificar que partes sea una lista de tuplas (nombre, longitud) ===
    if not partes or not isinstance(partes[0], tuple) or len(partes[0]) != 2:
        raise ValueError("El formato de 'partes' debe ser una lista de tuplas (nombre, longitud)")

    longitudes = [p[1] + cuchilla_corte for p in partes]

    for p in longitudes:
        if p > longitud_barra:
            raise ValueError(f"La parte de {p - cuchilla_corte}mm (con corte: {p}mm) no cabe en una barra de {longitud_barra}mm")

    # === Ordenar partes por longitud (descendente) para First Fit Decreasing ===
    partes_ordenadas = sorted(zip(partes, longitudes), key=lambda x: x[1], reverse=True)
    partes_nombres = [x[0] for x in partes_ordenadas]
    partes_longitudes = [x[1] for x in partes_ordenadas]

    barras = []

    for nombre_parte, longitud_parte in zip(partes_nombres, partes_longitudes):
        asignada = False
        # Buscar la barra con el menor resto que pueda alojar la parte
        barra_mejor = None
        for barra in barras:
            if barra['resto'] >= longitud_parte:
                if barra_mejor is None or barra['resto'] < barra_mejor['resto']:
                    barra_mejor = barra

        if barra_mejor:
            barra_mejor['partes'].append((nombre_parte, longitud_parte))
            barra_mejor['resto'] -= longitud_parte
            asignada = True

        if not asignada:
            nueva_barra = {
                'id': f"BAR-{len(barras) + 1:03d}",
                'partes': [(nombre_parte, longitud_parte)],
                'resto': longitud_barra - longitud_parte
            }
            barras.append(nueva_barra)

    return barras

def procesar_piezas_para_corte_optimizado(lista_piezas, limite_division=5995, longitud_barra=12000, cuchilla_corte=3):
    """
    Procesa una lista de piezas para optimizar el corte:
    1. Coloca piezas completas que caben en la barra.
    2. Divide piezas grandes (> longitud_barra) en tramos <= limite_division.
    3. Intenta combinar piezas chicas para minimizar desperdicio.
    4. Aplica criterio de división (10%-30%) solo a piezas entre 6000 y 7000 mm.
    Devuelve: (barras, partes_en_formato_correcto)
    """
    partes = []
    idx_parte = 1

    for p in lista_piezas:
        if p + cuchilla_corte <= longitud_barra:
            # Pieza cabe completa
            partes.append((f"P{idx_parte}a", p))
            idx_parte += 1
        else:
            # Pieza no cabe, dividir
            if 6000 <= p <= 7000:
                # === Aplicar criterio de división (10%-30%) ===
                cortes_posibles = generar_cortes_optimos(p, porcentaje_min=0.10, porcentaje_max=0.30, limite_minimo=1000)
                if cortes_posibles:
                    # Tomar el primer corte (podría optimizarse más)
                    corte1, corte2 = cortes_posibles[0]
                    partes.append((f"P{idx_parte}a", corte1))
                    partes.append((f"P{idx_parte}b", corte2))
                    idx_parte += 1
                else:
                    # Si no hay cortes válidos, usar división simple
                    restante = p
                    parte_letra = 'a'
                    while restante > 0:
                        if restante > limite_division:
                            partes.append((f"P{idx_parte}{parte_letra}", limite_division))
                            restante -= limite_division
                        else:
                            partes.append((f"P{idx_parte}{parte_letra}", restante))
                            restante = 0
                        parte_letra = chr(ord(parte_letra) + 1)
                    idx_parte += 1
            else:
                # Para piezas > 7000, usar división simple
                restante = p
                parte_letra = 'a'
                while restante > 0:
                    if restante > limite_division:
                        partes.append((f"P{idx_parte}{parte_letra}", limite_division))
                        restante -= limite_division
                    else:
                        partes.append((f"P{idx_parte}{parte_letra}", restante))
                        restante = 0
                    parte_letra = chr(ord(parte_letra) + 1)
                idx_parte += 1

    # === Garantizar que 'partes' sea una lista de tuplas (nombre, longitud) ===
    partes_correctas = []
    for p in partes:
        if isinstance(p, tuple) and len(p) == 2:
            partes_correctas.append(p)
        else:
            raise ValueError(f"Parte inválida: {p}. Formato debe ser (nombre, longitud)")

    # === Cortar barras con las partes generadas ===
    barras = cortar_barras_optimizadas(longitud_barra, partes_correctas, cuchilla_corte)

    # === Aplicar segundo filtro de optimización ===
    barras, partes_correctas = segundo_filtro_optimizacion(barras, partes_correctas, limite_division, longitud_barra, cuchilla_corte)

    return barras, partes_correctas  # <-- Devolver barras Y partes en formato correcto

def mostrar_plan_de_armado(partes, perfil, piezas_usadas_inventario):
    """
    Muestra cómo ensamblar cada pieza original usando sus partes.
    Incluye piezas usadas del inventario como piezas completas.
    Devuelve un diccionario con las piezas agrupadas por número de pieza.
    """
    print(f"\n" + "="*60)
    print(f"PLAN DE ARMADO PARA {perfil}:")
    print("="*60)

    # Agrupar partes por pieza original (índice)
    piezas_grupos = {}
    idx = 1
    for nombre, longitud in partes:
        # Extraer el número de la pieza (1, 2, 3, ...) de 'P1a', 'P2a', etc.
        if nombre.startswith('P'):
            pieza_num = int(nombre[1:-1])  # 'P1a' -> '1'
        else:
            pieza_num = int(nombre[:-1])  # '1a' -> '1'

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

    return piezas_grupos  # <-- Devolver el diccionario de piezas agrupadas

def segundo_filtro_optimizacion(barras, partes, limite_division=5995, longitud_barra=12000, cuchilla_corte=3):
    """
    Segundo filtro de optimización: intenta minimizar el desperdicio reubicando piezas chicas
    en barras con espacio libre, usando cortes de limite_division de piezas grandes si es útil.
    PRESERVA la estructura original de 'partes' para no alterar el plan de armado.
    """
    print("🔍 Aplicando segundo filtro de optimización global...")
    
    # === Separar piezas chicas y grandes ===
    piezas_chicas = [p for p in partes if p[1] <= limite_division]
    piezas_grandes = [p for p in partes if p[1] > limite_division]

    # === Buscar piezas chicas que no estén ubicadas ===
    piezas_chicas_no_ubicadas = []
    for pc in piezas_chicas:
        ubicada = False
        for barra in barras:
            for pb in barra['partes']:
                if pb[0] == pc[0]:  # Comparar por nombre
                    ubicada = True
                    break
            if ubicada:
                break
        if not ubicada:
            piezas_chicas_no_ubicadas.append(pc)

    if not piezas_chicas_no_ubicadas:
        print("✅ No hay piezas chicas por reubicar.")
        return barras, partes  # <-- Devolver partes originales sin modificar

    print(f"✅ Encontradas {len(piezas_chicas_no_ubicadas)} piezas chicas por reubicar.")

    # === Intentar reubicar piezas chicas en barras con espacio libre ===
    for pc in piezas_chicas_no_ubicadas:
        longitud_parte = pc[1] + cuchilla_corte
        barra_mejor = None

        # Buscar la barra con el menor resto que pueda alojar la parte
        for barra in barras:
            if barra['resto'] >= longitud_parte:
                if barra_mejor is None or barra['resto'] < barra_mejor['resto']:
                    barra_mejor = barra

        if barra_mejor:
            print(f"📦 Reubicando parte {pc[0]}({pc[1]}) en {barra_mejor['id']}")
            barra_mejor['partes'].append((pc[0], pc[1]))
            barra_mejor['resto'] -= longitud_parte
            # No quitar 'pc' de 'partes', porque el plan de armado depende de la estructura original

    # === Intentar usar cortes de piezas grandes para llenar espacios pequeños ===
    for pg in piezas_grandes:
        longitud_grande = pg[1]
        nombre_base = pg[0][:-1]  # 'P1a' -> 'P1'
        parte_letra = 'a'

        # Dividir pieza grande en tramos de limite_division
        partes_grande = []
        restante = longitud_grande
        while restante > 0:
            if restante > limite_division:
                partes_grande.append((f"{nombre_base}{parte_letra}", limite_division))
                restante -= limite_division
            else:
                partes_grande.append((f"{nombre_base}{parte_letra}", restante))
                restante = 0
            parte_letra = chr(ord(parte_letra) + 1)

        # Buscar barras con espacio para cada parte de la pieza grande
        for p in partes_grande:
            longitud_parte = p[1] + cuchilla_corte
            barra_mejor = None

            # Buscar la barra con el menor resto que pueda alojar la parte
            for barra in barras:
                if barra['resto'] >= longitud_parte:
                    if barra_mejor is None or barra['resto'] < barra_mejor['resto']:
                        barra_mejor = barra

            if barra_mejor:
                print(f"📦 Reubicando parte {p[0]}({p[1]}) de pieza grande en {barra_mejor['id']}")
                barra_mejor['partes'].append((p[0], p[1]))
                barra_mejor['resto'] -= longitud_parte
                # No quitar 'p' de 'partes', porque el plan de armado depende de la estructura original

    print("✅ Segundo filtro de optimización global completado.")
    return barras, partes  # <-- Devolver partes originales sin modificar

def procesar_piezas_para_corte_optimizado(lista_piezas, limite_division=5995, longitud_barra=12000, cuchilla_corte=3):
    """
    Procesa una lista de piezas para optimizar el corte:
    1. Coloca piezas completas que caben en la barra.
    2. Divide piezas grandes (> longitud_barra) en tramos <= limite_division.
    3. Intenta combinar piezas chicas para minimizar desperdicio.
    """
    partes = []
    idx_parte = 1

    # === Separar piezas chicas y grandes ===
    piezas_chicas = []
    piezas_grandes = []
    for p in lista_piezas:
        if p + cuchilla_corte <= longitud_barra:
            piezas_chicas.append(p)
        else:
            piezas_grandes.append(p)

    # === Procesar piezas grandes ===
    for p in piezas_grandes:
        if p + cuchilla_corte <= longitud_barra:
            # Pieza cabe completa
            partes.append((f"P{idx_parte}a", p))
            idx_parte += 1
        else:
            # Pieza no cabe, dividir en tramos <= limite_division
            if 6000 <= p <= 7000:
                # === Aplicar criterio de división (10%-30%) ===
                cortes_posibles = generar_cortes_optimos(p, porcentaje_min=0.10, porcentaje_max=0.30, limite_minimo=1000)
                if cortes_posibles:
                    # Tomar el primer corte (podría optimizarse más)
                    corte1, corte2 = cortes_posibles[0]
                    partes.append((f"P{idx_parte}a", corte1))
                    partes.append((f"P{idx_parte}b", corte2))
                    idx_parte += 1
                else:
                    # Si no hay cortes válidos, usar división simple
                    restante = p
                    parte_letra = 'a'
                    while restante > 0:
                        if restante > limite_division:
                            partes.append((f"P{idx_parte}{parte_letra}", limite_division))
                            restante -= limite_division
                        else:
                            partes.append((f"P{idx_parte}{parte_letra}", restante))
                            restante = 0
                        parte_letra = chr(ord(parte_letra) + 1)
                    idx_parte += 1
            else:
                # Para piezas > 7000, usar división simple
                restante = p
                parte_letra = 'a'
                while restante > 0:
                    if restante > limite_division:
                        partes.append((f"P{idx_parte}{parte_letra}", limite_division))
                        restante -= limite_division
                    else:
                        partes.append((f"P{idx_parte}{parte_letra}", restante))
                        restante = 0
                    parte_letra = chr(ord(parte_letra) + 1)
                idx_parte += 1

    # === Procesar piezas chicas ===
    for p in piezas_chicas:
        partes.append((f"P{idx_parte}a", p))
        idx_parte += 1

    # === Cortar barras con las partes generadas ===
    barras = cortar_barras_optimizadas(longitud_barra, partes, cuchilla_corte)

    # === Aplicar segundo filtro de optimización ===
    barras, partes = segundo_filtro_optimizacion(barras, partes, limite_division, longitud_barra, cuchilla_corte)

    return barras, partes
