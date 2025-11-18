import matplotlib
matplotlib.use('Agg')  # <-- Añadir esta línea ANTES de importar pyplot
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import random  # Importar random
from config import Config

def graficar_barras_estandar(barras, perfil, piezas_usadas_inventario, output_folder):
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
        return None

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

    # Sanitizar el nombre del perfil para usarlo en el nombre del archivo
    nombre_perfil_sanitizado = "".join(c for c in perfil if c.isalnum() or c in " _-")
    filename = f"grafico_corte_{nombre_perfil_sanitizado}.png"
    filepath = os.path.join(output_folder, filename)
    plt.savefig(filepath)
    plt.close(fig)
    print(f"📊 Gráfico de corte guardado: {filepath}")

    return filename


def graficar_plan_de_armado(plan_armado, perfil, output_folder):
    """
    Grafica cómo ensamblar cada pieza original usando sus partes.
    Incluye piezas usadas del inventario como piezas completas.
    """
    print(f"\n📊 Mostrando plan de armado gráfico para {perfil}...")

    # Calcular tamaño del gráfico
    num_piezas = len(plan_armado)
    if num_piezas == 0:
        print(f"No hay piezas para graficar en {perfil}.")
        return None

    fig, ax = plt.subplots(figsize=(14, max(4, num_piezas * 0.6)))

    # Generar colores
    colores = []
    for _ in range(100):
        r = random.uniform(0.3, 0.85)
        g = random.uniform(0.3, 0.85)
        b = random.uniform(0.3, 0.85)
        colores.append((r, g, b))

    for i, (pieza_num, partes_pieza) in enumerate(sorted(plan_armado.items())):
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

    # Sanitizar el nombre del perfil para usarlo en el nombre del archivo
    nombre_perfil_sanitizado = "".join(c for c in perfil if c.isalnum() or c in " _-")
    filename = f"grafico_armado_{nombre_perfil_sanitizado}.png"
    filepath = os.path.join(output_folder, filename)
    plt.savefig(filepath)
    plt.close(fig)
    print(f"📊 Gráfico de armado guardado: {filepath}")

    return filename