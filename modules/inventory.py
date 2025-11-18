def leer_inventario(ruta_inventario):
    """
    Lee un archivo de inventario y devuelve un diccionario de piezas disponibles.
    Formato esperado: Perfil;Longitud;Cantidad;Ubicacion
    """
    inventario = {}

    with open(ruta_inventario, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            # === Ignorar líneas vacías o con Sub total, Total:, Profile ===
            if not linea or "Sub total" in linea or "Total:" in linea or "Profile" in linea:
                continue

            partes = linea.split(';')
            if len(partes) < 3:
                continue

            perfil = partes[0].strip()
            # === Limpiar caracteres raros del nombre del perfil ===
            perfil = "".join(c for c in perfil if c.isalnum() or c in " _-*")

            if not perfil:
                continue

            try:
                cantidad = int(partes[2].strip())
                longitud_mm = int(partes[3].strip())
                if perfil not in inventario:
                    inventario[perfil] = []
                inventario[perfil].extend([longitud_mm] * cantidad)
            except (ValueError, IndexError):
                # === Ignorar filas con valores no numéricos ===
                continue

    return inventario