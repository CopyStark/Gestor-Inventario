import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="Gestor de Inventario")

def load_data():
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
    
    except FileNotFoundError:
        return None, None
    
    except KeyError as e:
        return None, None

    except ValueError as e:
        return None, None

def update_statuses(df_productos):
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

if 'data_loaded' not in st.session_state:
    df_productos, df_movimientos = load_data()
    if df_productos is not None:
        st.session_state.df_productos = df_productos
        st.session_state.df_movimientos = df_movimientos
        st.session_state.data_loaded = True

if 'data_loaded' in st.session_state:
    
    st.session_state.df_productos = update_statuses(st.session_state.df_productos)

    product_map_name_to_id = dict(zip(st.session_state.df_productos['Nombre'], st.session_state.df_productos['Codigo']))
    product_map_id_to_name = dict(zip(st.session_state.df_productos['Codigo'], st.session_state.df_productos['Nombre']))

    st.title("🛒 Gestor de Inventario Simple")

    tab1, tab2 = st.tabs(["Inventario Actual", "Registrar Movimiento"])

    with tab1:
        st.header("Estado del Inventario")
        
        st.subheader("Alertas ⚠️")
        col1, col2 = st.columns(2)
        with col1:
            st.write("Stock Crítico")
            alert_stock = st.session_state.df_productos[
                st.session_state.df_productos['Estado (Stock)'].isin(["🔴 CRÍTICO", "🟡 ADVERTENCIA"])
            ]
            st.dataframe(alert_stock[["Nombre", "Stock_Actual", "Stock_Minimo", "Estado (Stock)"]], use_container_width=True)

        with col2:
            st.write("Vencimiento")
            alert_venc = st.session_state.df_productos[
                st.session_state.df_productos['Estado (Vencimiento)'].isin(["🔴 VENCIDO", "🟡 PRÓXIMO A VENCER"])
            ]
            st.dataframe(alert_venc[["Nombre", "Fecha_Vencimiento", "Estado (Vencimiento)"]], use_container_width=True)
        
        st.divider()

        st.subheader("Inventario Completo")
        
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            categorias = ["Todas"] + list(st.session_state.df_productos["Categoria"].unique())
            cat_filter = st.selectbox("Filtrar por Categoría:", options=categorias)
        
        with col_f2:
            search_term = st.text_input("Buscar por Nombre:", placeholder="Ej: Leche Entera")

        df_display = st.session_state.df_productos.copy()
        if cat_filter != "Todas":
            df_display = df_display[df_display["Categoria"] == cat_filter]
        if search_term:
            df_display = df_display[df_display["Nombre"].str.contains(search_term, case=False)]

        st.dataframe(df_display, use_container_width=True)

    with tab2:
        st.header("Registrar Nuevo Movimiento")
        
        with st.form("nuevo_movimiento_form"):
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                producto_nombre = st.selectbox(
                    "Producto:", 
                    options=st.session_state.df_productos["Nombre"]
                )
                tipo_movimiento = st.radio(
                    "Tipo de Movimiento:", 
                    ["Entrada", "Salida"], 
                    horizontal=True
                )
            
            with col_m2:
                cantidad = st.number_input("Cantidad:", min_value=1, step=1)
                responsable = st.text_input("Responsable:", "Vendedor1")
            
            submitted = st.form_submit_button("Registrar Movimiento")

        if submitted:
            codigo_producto = product_map_name_to_id[producto_nombre]
            fecha_actual = pd.to_datetime(datetime.now().date())
            
            idx = st.session_state.df_productos.index[
                st.session_state.df_productos['Codigo'] == codigo_producto
            ].tolist()[0]
            
            stock_actual = st.session_state.df_productos.at[idx, 'Stock_Actual']

            if tipo_movimiento == "Salida" and cantidad > stock_actual:
                pass # No se registra el movimiento si no hay stock
            
            else:
                if tipo_movimiento == "Entrada":
                    nuevo_stock = stock_actual + cantidad
                    st.session_state.df_productos.at[idx, 'Fecha_Entrada'] = fecha_actual
                else: 
                    nuevo_stock = stock_actual - cantidad
                
                st.session_state.df_productos.at[idx, 'Stock_Actual'] = nuevo_stock
                
                nuevo_movimiento = pd.DataFrame({
                    "Fecha": [fecha_actual],
                    "Codigo_Producto": [codigo_producto],
                    "Tipo": [tipo_movimiento],
                    "Cantidad": [cantidad],
                    "Responsable": [responsable]
                })
                
                st.session_state.df_movimientos = pd.concat(
                    [st.session_state.df_movimientos, nuevo_movimiento], 
                    ignore_index=True
                )
                
                st.success(f"¡Movimiento '{tipo_movimiento}' de {cantidad} unidad(es) de '{producto_nombre}' registrado!")
                
                st.session_state.df_productos = update_statuses(st.session_state.df_productos)
                st.rerun()

        st.divider()

        st.header("Historial de Movimientos")
        
        df_historial = st.session_state.df_movimientos.copy()
        
        try:
            df_historial["Nombre Producto"] = df_historial["Codigo_Producto"].map(product_map_id_to_name)
            column_order = ["Fecha", "Nombre Producto", "Tipo", "Cantidad", "Responsable", "Codigo_Producto"]
            
            st.dataframe(
                df_historial[column_order].sort_values(by="Fecha", ascending=False), 
                use_container_width=True
            )
        except KeyError as e:
            pass # No mostrar error si falla el historial
