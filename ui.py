# ui.py
import streamlit as st
import pandas as pd
from datetime import datetime
from logica import update_statuses, save_data # Importamos las funciones de logica

def mostrar_tab_inventario():
    """Dibuja la pestaña 'Inventario Actual'."""
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

def mostrar_tab_movimiento():
    """Dibuja la pestaña 'Registrar Movimiento'."""
    st.header("Registrar Nuevo Movimiento")
    
    product_map_name_to_id = dict(zip(st.session_state.df_productos['Nombre'], st.session_state.df_productos['Codigo']))

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
            st.error(f"Error: No hay suficiente stock de '{producto_nombre}'. Stock actual: {stock_actual}")
        
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
            
            # --- ¡NUEVO! Guardamos los cambios en los CSV ---
            save_data(st.session_state.df_productos, st.session_state.df_movimientos)
            
            st.success(f"¡Movimiento '{tipo_movimiento}' de {cantidad} unidad(es) de '{producto_nombre}' registrado!")
            
            st.session_state.df_productos = update_statuses(st.session_state.df_productos)
            st.rerun()

    st.divider()

    st.header("Historial de Movimientos")
    
    product_map_id_to_name = dict(zip(st.session_state.df_productos['Codigo'], st.session_state.df_productos['Nombre']))
    df_historial = st.session_state.df_movimientos.copy()
    
    try:
        df_historial["Nombre Producto"] = df_historial["Codigo_Producto"].map(product_map_id_to_name)
        column_order = ["Fecha", "Nombre Producto", "Tipo", "Cantidad", "Responsable", "Codigo_Producto"]
        
        st.dataframe(
            df_historial[column_order].sort_values(by="Fecha", ascending=False), 
            use_container_width=True
        )
    except KeyError:
        pass # Falla silenciosamente