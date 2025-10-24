import streamlit as st
import pandas as pd
from datetime import datetime

def load_data():
    """Carga los CSV a la memoria."""
    df_productos = None
    df_movimientos = None
    try:
        df_productos = pd.read_csv("Productos.csv", sep=";")
        df_movimientos = pd.read_csv("Movimientos.csv", sep=";")

        df_productos.columns = df_productos.columns.str.strip()
        df_movimientos.columns = df_movimientos.columns.str.strip()

        date_format = "%d-%m-%Y"
        
        df_productos["Fecha_Entrada"] = pd.to_datetime(df_productos["Fecha_Entrada"], format=date_format)
        df_productos["Fecha_Vencimiento"] = pd.to_datetime(df_productos["Fecha_Vencimiento"], format=date_format)
        df_movimientos["Fecha"] = pd.to_datetime(df_movimientos["Fecha"], format=date_format)

        return df_productos, df_movimientos
    
    except (FileNotFoundError, KeyError, ValueError):
        return None, None # Falla silenciosamente

def update_statuses(df_productos):
    """Calcula el estado de stock y vencimiento."""
    today = pd.to_datetime(datetime.now().date())
    
    df_productos['Estado (Stock)'] = df_productos.apply(
        lambda row: "🔴 CRÍTICO" if row['Stock_Actual'] < row['Stock_Minimo'] 
                      else ("🟡 ADVERTENCIA" if row['Stock_Actual'] < (row['Stock_Minimo'] * 1.2) 
                            else "🟢 ÓPTIMO"),
        axis=1
    )
    
    dias_para_vencer = (df_productos['Fecha_Vencimiento'] - today).dt.days
    
    df_productos['Estado (Vencimiento)'] = "🟢 OK"
    df_productos.loc[dias_para_vencer <= 7, 'Estado (Vencimiento)'] = "🟡 PRÓXIMO A VENCER"
    df_productos.loc[dias_para_vencer < 0, 'Estado (Vencimiento)'] = "🔴 VENCIDO"
    
    return df_productos

def save_data(df_productos, df_movimientos):
    """Guarda los dataframes de vuelta en los archivos CSV."""
    
    # Preparamos una copia para guardar y evitar problemas de formato
    productos_para_guardar = df_productos.copy()
    movimientos_para_guardar = df_movimientos.copy()
    
    # Convertimos las fechas de vuelta a string DD-MM-YYYY
    date_format = "%d-%m-%Y"
    productos_para_guardar["Fecha_Entrada"] = productos_para_guardar["Fecha_Entrada"].dt.strftime(date_format)
    productos_para_guardar["Fecha_Vencimiento"] = productos_para_guardar["Fecha_Vencimiento"].dt.strftime(date_format)
    movimientos_para_guardar["Fecha"] = movimientos_para_guardar["Fecha"].dt.strftime(date_format)

    try:
        productos_para_guardar.to_csv("Productos.csv", sep=";", index=False)
        movimientos_para_guardar.to_csv("Movimientos.csv", sep=";", index=False)
    except Exception as e:
        st.error(f"Error al guardar los datos: {e}")