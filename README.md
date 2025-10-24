# 🛒 Gestor de Inventario con Streamlit

Una aplicación web simple para la gestión de un inventario básico, desarrollada en Python con la biblioteca Streamlit.

## 🚀 Tecnologías Utilizadas

* **Python 3**
* **Streamlit** (para la interfaz web)
* **Pandas** (para la manipulación de datos)
* **Git / GitHub** (para el control de versiones)

## 📁 Estructura de Datos

El proyecto se basa en dos archivos `.csv` que actúan como base de datos:

1.  **`Productos.csv`**: Contiene la lista maestra de productos, su categoría, stock inicial, stock actual, stock mínimo y fechas de vencimiento.
2.  **`Movimientos.csv`**: Es un registro histórico de todas las entradas y salidas de productos.

**Nota Importante:** Ambos archivos `.csv` utilizan un **punto y coma (`;`)** como separador de columnas.

## ⚙️ Cómo Ejecutar el Proyecto

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

**1. Clonar el Repositorio**

```bash
git clone [https://github.com/CopyStark/Gestor-Inventario.git](https://github.com/CopyStark/Gestor-Inventario.git)
cd Gestor-Inventario

# Crear el entorno
python -m venv venv

# Activar en Windows
.\venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py
