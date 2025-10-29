import streamlit as st
import pandas as pd
from datetime import datetime
import time # Importado para el spinner

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(layout="wide", page_title="Gestor de Inventario")

# --- 2. GESTIÓN DE DATOS (CARGAR Y GUARDAR) ---

def load_data():
    """
    Carga los archivos CSV.
    Convierte las fechas al formato correcto (solo fecha, sin hora).
    """
    try:
        df_productos = pd.read_csv("Productos.csv", sep=";")
        df_movimientos = pd.read_csv("Movimientos.csv", sep=";")

        # Limpiar nombres de columnas
        df_productos.columns = df_productos.columns.str.strip()
        df_movimientos.columns = df_movimientos.columns.str.strip()
        
        # --- Conversión de Fechas (Solo Fecha) ---
        # Usar dayfirst=True para formato DD-MM-YYYY.
        # .dt.date para descartar la hora si es que existe.
        
        df_productos["Fecha_Entrada"] = pd.to_datetime(df_productos["Fecha_Entrada"], dayfirst=True, errors='coerce').dt.normalize()
        df_productos["Fecha_Vencimiento"] = pd.to_datetime(df_productos["Fecha_Vencimiento"], dayfirst=True, errors='coerce').dt.normalize()
        df_movimientos["Fecha"] = pd.to_datetime(df_movimientos["Fecha"], dayfirst=True, errors='coerce').dt.normalize()

        # Verificar si alguna fecha importante se volvió NaT por error
        if "Fecha_Entrada" in df_productos.columns and df_productos["Fecha_Entrada"].isnull().any():
            st.warning("Advertencia: Algunas fechas de entrada no pudieron ser leídas. Revisa el formato en Productos.csv.")
        if "Fecha" in df_movimientos.columns and df_movimientos["Fecha"].isnull().any():
            st.warning("Advertencia: Algunas fechas de movimiento no pudieron ser leídas. Revisa el formato en Movimientos.csv.")

        return df_productos, df_movimientos
    
    except FileNotFoundError:
        st.error("Error: No se encontraron los archivos 'Productos.csv' o 'Movimientos.csv'.")
        st.info("Asegúrate de que los archivos CSV estén en la misma carpeta que app.py.")
        return None, None
    
    except KeyError as e:
        st.error(f"Error: Falta una columna esencial en los archivos CSV: {e}")
        return None, None

    except ValueError as e:
        st.error(f"Error en el formato de datos: {e}. Asegúrate de que las fechas estén en formato DD-MM-YYYY.")
        return None, None

def save_data(df_productos, df_movimientos):
    """
    Guarda los DataFrames de vuelta a CSV.
    Guarda las fechas solo en formato DD-MM-YYYY.
    """
    # Formato de guardado: solo fecha
    date_format_string = "%d-%m-%Y"
    
    # Copiar para evitar modificar el dataframe en sesión
    df_prod_save = df_productos.copy()
    df_mov_save = df_movimientos.copy()

    # Convertir fechas de productos a string (solo fecha)
    df_prod_save["Fecha_Entrada"] = df_prod_save["Fecha_Entrada"].dt.strftime(date_format_string)
    df_prod_save["Fecha_Vencimiento"] = df_prod_save["Fecha_Vencimiento"].apply(
        lambda x: x.strftime(date_format_string) if pd.notnull(x) else ""
    )
    
    # Convertir fechas de movimientos a string (solo fecha)
    df_mov_save["Fecha"] = df_mov_save["Fecha"].dt.strftime(date_format_string)

    # Guardar en CSV
    df_prod_save.to_csv("Productos.csv", sep=";", index=False)
    df_mov_save.to_csv("Movimientos.csv", sep=";", index=False)

def update_statuses(df_productos):
    """
    Calcula y actualiza las columnas de 'Estado (Stock)' y 'Estado (Vencimiento)'
    """
    if df_productos.empty:
        return df_productos

    # Obtener solo la fecha de hoy, normalizada (sin hora)
    today = pd.to_datetime(datetime.now().date())
    
    # 1. Estado de Stock
    df_productos['Estado (Stock)'] = df_productos.apply(
        lambda row: "🔴 CRÍTICO" if row['Stock_Actual'] < row['Stock_Minimo'] 
                      else ("🟡 ADVERTENCIA" if row['Stock_Actual'] < (row['Stock_Minimo'] * 1.5) 
                            else "🟢 ÓPTIMO"),
        axis=1
    )
    
    # 2. Estado de Vencimiento
    # Asegurarse de que las fechas de vencimiento estén normalizadas (solo fecha)
    df_productos['Fecha_Vencimiento'] = pd.to_datetime(df_productos['Fecha_Vencimiento']).dt.normalize()
    
    dias_para_vencer = (df_productos['Fecha_Vencimiento'] - today).dt.days
    
    df_productos['Estado (Vencimiento)'] = "🟢 OK"
    df_productos.loc[dias_para_vencer <= 7, 'Estado (Vencimiento)'] = "🟡 PRÓXIMO A VENCER"
    df_productos.loc[dias_para_vencer < 0, 'Estado (Vencimiento)'] = "🔴 VENCIDO"
    df_productos.loc[pd.isna(df_productos['Fecha_Vencimiento']), 'Estado (Vencimiento)'] = "⚪ N/A"
    
    return df_productos

# --- 3. FUNCIONES DE LAS PÁGINAS ---

def mostrar_footer():
    """
    Muestra un footer estándar en la parte inferior de la página.
    """
    st.divider()
    
    col_f1, col_f2 = st.columns(2)
        
    with col_f1:
        st.subheader("Servicio al Cliente")
        st.caption("¿Problemas con la app? Contacta a soporte:")
        st.caption("📧 Correo: soporte@gestor.com")
        st.caption("📞 Teléfono: +56 9 1234 5678")

    with col_f2:
        st.subheader("Autenticación")
        st.caption("© 2024 - Equipo Gestor. Todos los derechos reservados.")
        st.caption("Plataforma interna de gestión.")

def mostrar_inventario(df_productos):
    """
    Renderiza la página "Inventario Actual".
    """
    st.header("Estado del Inventario")
    
    # --- Alertas ---
    st.subheader("Alertas ⚠️")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Stock Crítico/Advertencia")
        alert_stock = df_productos[
            df_productos['Estado (Stock)'].isin(["🔴 CRÍTICO", "🟡 ADVERTENCIA"])
        ]
        st.dataframe(alert_stock[["Nombre", "Stock_Actual", "Stock_Minimo", "Estado (Stock)"]], use_container_width=True)

    with col2:
        st.write("Vencimiento Próximo/Vencido")
        alert_venc = df_productos[
            df_productos['Estado (Vencimiento)'].isin(["🔴 VENCIDO", "🟡 PRÓXIMO A VENCER"])
        ]
        st.dataframe(alert_venc[["Nombre", "Fecha_Vencimiento", "Estado (Vencimiento)"]], use_container_width=True,
                     column_config={
                         "Fecha_Vencimiento": st.column_config.DateColumn("Fecha Vencimiento", format="DD-MM-YYYY")
                     })
    
    st.divider()

    # --- Inventario Completo ---
    st.subheader("Inventario Completo")
    
    # Filtros
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        if "Categoria" in df_productos.columns and not df_productos["Categoria"].empty:
            categorias = ["Todas"] + list(df_productos["Categoria"].unique())
        else:
            categorias = ["Todas"]
        cat_filter = st.selectbox("Filtrar por Categoría:", options=categorias)
    
    with col_f2:
        search_term = st.text_input("Buscar por Nombre:", placeholder="Ej: Leche Entera")

    # Aplicar filtros
    df_display = df_productos.copy()
    if cat_filter != "Todas":
        df_display = df_display[df_display["Categoria"] == cat_filter]
    if search_term:
        df_display = df_display[df_display["Nombre"].str.contains(search_term, case=False)]

    # Mostrar tabla de inventario
    st.dataframe(df_display, use_container_width=True,
                 column_config={
                     "Fecha_Entrada": st.column_config.DateColumn("Fecha Entrada", format="DD-MM-YYYY"),
                     "Fecha_Vencimiento": st.column_config.DateColumn("Fecha Vencimiento", format="DD-MM-YYYY"),
                     "Precio_Unitario": st.column_config.NumberColumn("Precio Unitario", format="$ %d")
                 })

    mostrar_footer()

def registrar_movimiento(df_productos, df_movimientos, product_map_name_to_id, product_map_id_to_name):
    """
    Renderiza la página "Registrar Movimiento".
    Usa solo la fecha (sin hora) para el registro.
    """
    st.header("Registrar Nuevo Movimiento")
    
    # --- Formulario ---
    col_f1, col_form, col_f3 = st.columns([1, 2, 1])
    
    with col_form:
        with st.form("nuevo_movimiento_form"):
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                producto_nombre = st.selectbox(
                    "Producto:", 
                    options=df_productos["Nombre"]
                )
                tipo_movimiento = st.radio(
                    "Tipo de Movimiento:", 
                    ["Entrada", "Salida"], 
                    horizontal=True
                )
            
            with col_m2:
                cantidad = st.number_input("Cantidad:", min_value=1, step=1)
                responsable = st.text_input("Responsable:", placeholder="Ej: Vendedor1")
            
            submitted = st.form_submit_button("Registrar Movimiento")

        if submitted:
            if not responsable:
                st.warning("El campo 'Responsable' no puede estar vacío.")
            else:
                # Lógica de registro
                codigo_producto = product_map_name_to_id[producto_nombre]
                
                # --- CAMBIO: Usar solo la fecha de hoy (sin hora) ---
                fecha_actual = pd.to_datetime(datetime.now().date())
                
                idx = df_productos.index[df_productos['Codigo'] == codigo_producto].tolist()[0]
                stock_actual = df_productos.at[idx, 'Stock_Actual']

                if tipo_movimiento == "Salida" and cantidad > stock_actual:
                    st.error(f"Error: No hay stock suficiente. Stock actual: {stock_actual}")
                
                else:
                    with st.spinner("Registrando y guardando..."):
                        if tipo_movimiento == "Entrada":
                            nuevo_stock = stock_actual + cantidad
                            st.session_state.df_productos.at[idx, 'Fecha_Entrada'] = fecha_actual
                        else: # Salida
                            nuevo_stock = stock_actual - cantidad
                        
                        st.session_state.df_productos.at[idx, 'Stock_Actual'] = nuevo_stock
                        
                        nuevo_movimiento = pd.DataFrame({
                            "Fecha": [fecha_actual], # Solo fecha
                            "Codigo_Producto": [codigo_producto],
                            "Tipo": [tipo_movimiento],
                            "Cantidad": [cantidad],
                            "Responsable": [responsable]
                        })
                        
                        st.session_state.df_movimientos = pd.concat(
                            [st.session_state.df_movimientos, nuevo_movimiento], 
                            ignore_index=True
                        )
                        
                        save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                        st.success(f"¡Movimiento '{tipo_movimiento}' de {cantidad} unidad(es) de '{producto_nombre}' registrado!")
                        st.session_state.df_productos = update_statuses(st.session_state.df_productos)
                        time.sleep(1)
                        st.rerun()

    st.divider()

    # --- Historial de Movimientos ---
    st.header("Historial de Movimientos")
    
    df_historial = df_movimientos.copy()
    
    try:
        df_historial["Nombre Producto"] = df_historial["Codigo_Producto"].map(product_map_id_to_name)
        column_order = ["Fecha", "Nombre Producto", "Tipo", "Cantidad", "Responsable", "Codigo_Producto"]
        
        st.dataframe(
            df_historial[column_order].sort_values(by="Fecha", ascending=False), 
            use_container_width=True,
            column_config={
                # --- CAMBIO: Mostrar solo fecha en el historial ---
                "Fecha": st.column_config.DateColumn("Fecha", format="DD-MM-YYYY")
            }
        )
    except KeyError as e:
        st.warning("No se pudo cargar el historial de movimientos.")

    mostrar_footer()

def anadir_nuevo_producto(df_productos):
    """
    Renderiza la página "Añadir Nuevo Producto".
    Usa solo la fecha (sin hora) para la creación.
    """
    st.header("Añadir Nuevo Producto al Inventario")
    
    col1, col_form, col3 = st.columns([1, 2, 1])

    with col_form:
        st.subheader("Detalles del Nuevo Producto")
        sin_vencimiento = st.checkbox("Este producto no tiene vencimiento")

    with col_form.form("nuevo_producto_form"):
        nombre = st.text_input("Nombre del Producto:")
        categoria = st.text_input("Categoría:", "General")
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            stock_inicial = st.number_input("Stock Inicial:", min_value=0, step=1)
        with col_s2:
            stock_minimo = st.number_input("Stock Mínimo:", min_value=0, step=1)
        with col_s3:
            precio_unitario = st.number_input("Precio Unitario:", min_value=0, step=1)
        
        fecha_vencimiento = None
        if sin_vencimiento:
            pass # No muestra el selector
        else:
            # Muestra el selector, por defecto con la fecha de hoy
            fecha_vencimiento = st.date_input("Fecha de Vencimiento:", datetime.now())
        
        submitted = st.form_submit_button("Añadir Producto")

    if submitted:
        if not nombre:
            col_form.warning("El campo 'Nombre del Producto' no puede estar vacío.")
        elif nombre in df_productos["Nombre"].values:
            col_form.warning("Error: Ya existe un producto con ese nombre.")
        else:
            with col_form:
                with st.spinner("Añadiendo producto..."):
                    
                    if df_productos.empty:
                        nuevo_codigo = 1
                    else:
                        nuevo_codigo = df_productos['Codigo'].max() + 1
                    
                    fecha_venc_final = None
                    if sin_vencimiento:
                        fecha_venc_final = pd.NaT
                    else:
                        # Asegurarse de guardar solo la fecha
                        fecha_venc_final = pd.to_datetime(fecha_vencimiento)
                    
                    # --- CAMBIO: Usar solo la fecha (sin hora) para la entrada ---
                    fecha_entrada = pd.to_datetime(datetime.now().date())
                    
                    nuevo_producto = pd.DataFrame({
                        "Codigo": [nuevo_codigo],
                        "Nombre": [nombre],
                        "Categoria": [categoria],
                        "Stock_Inicial": [stock_inicial],
                        "Stock_Actual": [stock_inicial],
                        "Stock_Minimo": [stock_minimo],
                        "Fecha_Entrada": [fecha_entrada], # Solo fecha
                        "Fecha_Vencimiento": [fecha_venc_final],
                        "Precio_Unitario": [precio_unitario]
                    })
                    
                    st.session_state.df_productos = pd.concat(
                        [st.session_state.df_productos, nuevo_producto],
                        ignore_index=True
                    )
                    
                    save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                    
                    st.success(f"¡Producto '{nombre}' (Código: {nuevo_codigo}) añadido con éxito!")
                    time.sleep(2)
                    st.rerun()

    mostrar_footer()


def gestionar_productos(df_productos):
    """
    Renderiza la página "Gestionar Productos".
    """
    st.header("Gestionar Productos Existentes")

    if df_productos.empty:
        st.warning("No hay productos en el inventario para gestionar.")
        mostrar_footer()
        return

    lista_nombres = [""] + list(df_productos["Nombre"])
    
    if 'producto_seleccionado' not in st.session_state:
        st.session_state.producto_seleccionado = ""

    def actualizar_seleccion():
        st.session_state.producto_seleccionado = st.session_state.widget_producto_select
    
    nombre_producto = st.selectbox(
        "Selecciona un producto para editar o eliminar:", 
        options=lista_nombres,
        key="widget_producto_select",
        on_change=actualizar_seleccion
    )

    nombre_producto = st.session_state.producto_seleccionado
    
    if nombre_producto:
        try:
            idx = df_productos.index[df_productos['Nombre'] == nombre_producto].tolist()[0]
            producto_data = df_productos.loc[idx]
        except IndexError:
            st.error("Error: No se pudo encontrar el producto. Por favor, refresca la página.")
            st.session_state.producto_seleccionado = ""
            st.rerun()
            return

        # Formulario de Edición
        st.subheader(f"Editando: {nombre_producto}")
        with st.form("editar_producto_form"):
            categoria = st.text_input("Categoría:", value=producto_data["Categoria"])
            stock_minimo = st.number_input("Stock Mínimo:", min_value=0, step=1, value=int(producto_data["Stock_Minimo"]))
            precio_unitario = st.number_input("Precio Unitario:", min_value=0, step=1, value=int(producto_data["Precio_Unitario"]))
            
            submitted_edit = st.form_submit_button("Guardar Cambios")

        if submitted_edit:
            with st.spinner("Guardando cambios..."):
                st.session_state.df_productos.at[idx, "Categoria"] = categoria
                st.session_state.df_productos.at[idx, "Stock_Minimo"] = stock_minimo
                st.session_state.df_productos.at[idx, "Precio_Unitario"] = precio_unitario
                
                save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                st.success(f"¡Producto '{nombre_producto}' actualizado con éxito!")
                time.sleep(1)
                st.rerun()

        # Zona de Eliminación
        st.divider()
        st.subheader("Zona de Peligro: Eliminar Producto")
        st.warning(f"Advertencia: Estás a punto de eliminar '{nombre_producto}' permanentemente. Esta acción no se puede deshacer.")
        
        confirm_delete = st.checkbox("Sí, estoy seguro de que quiero eliminar este producto.")
        
        if st.button("Eliminar Producto Permanentemente", disabled=not confirm_delete, type="primary"):
            with st.spinner("Eliminando producto..."):
                st.session_state.df_productos = st.session_state.df_productos.drop(index=idx).reset_index(drop=True)
                
                save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                st.success(f"¡Producto '{nombre_producto}' eliminado con éxito!")
                
                st.session_state.producto_seleccionado = ""
                time.sleep(2)
                st.rerun()
    
    mostrar_footer()


def mostrar_login():
    """
    Muestra la pantalla de inicio de sesión (Versión Centrada).
    """
    
    col1, col_form, col3 = st.columns([1, 2, 1])

    with col_form:
        
        st.title("Gestor de Inventario")
        st.subheader("Por favor, inicie sesión para continuar")
        
        with st.form("login_form"):
            email = st.text_input("Correo Electrónico", placeholder="ejemplo@correo.com")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar")
            
            if submitted:
                if email and password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.warning("Por favor, ingresa tu correo y contraseña.")

    st.divider()
    st.caption("© 2024 - Equipo Gestor. Todos los derechos reservados.")


# --- 4. CÓDIGO PRINCIPAL (MODIFICADO CON LÓGICA DE LOGIN) ---

if 'data_loaded' not in st.session_state:
    df_productos, df_movimientos = load_data()
    if df_productos is not None:
        st.session_state.df_productos = df_productos
        st.session_state.df_movimientos = df_movimientos
        st.session_state.data_loaded = True
        st.session_state.logged_in = False
    
if 'data_loaded' in st.session_state:
    
    if st.session_state.logged_in:
        
        # 1. Actualiza los estados de los productos
        st.session_state.df_productos = update_statuses(st.session_state.df_productos)

        # 2. Crea los mapas de IDs/Nombres
        product_map_name_to_id = dict(zip(st.session_state.df_productos['Nombre'], st.session_state.df_productos['Codigo']))
        product_map_id_to_name = dict(zip(st.session_state.df_productos['Codigo'], st.session_state.df_productos['Nombre']))

        # 3. Título principal de la App
        st.title("Gestor de Inventario")

        # 4. Menú Lateral (Sidebar)
        with st.sidebar:
            st.header("Navegación")
            
            menu_options = ["Inventario Actual", "Registrar Movimiento", "Añadir Nuevo Producto", "Gestionar Productos"]
            
            if 'page' not in st.session_state:
                st.session_state.page = "Inventario Actual"
            
            current_page_index = menu_options.index(st.session_state.page)
            
            page = st.radio(
                "Selecciona una página:",
                menu_options,
                index=current_page_index
            )
            st.session_state.page = page
            
            st.divider()
            
            if st.button("Cerrar Sesión"):
                st.session_state.logged_in = False
                st.rerun()

        # 5. Muestra la página seleccionada
        if st.session_state.page == "Inventario Actual":
            mostrar_inventario(st.session_state.df_productos)
            
        elif st.session_state.page == "Registrar Movimiento":
            registrar_movimiento(
                st.session_state.df_productos, 
                st.session_state.df_movimientos,
                product_map_name_to_id, 
                product_map_id_to_name
            )
            
        elif st.session_state.page == "Añadir Nuevo Producto":
            anadir_nuevo_producto(st.session_state.df_productos)
        
        elif st.session_state.page == "Gestionar Productos":
            gestionar_productos(st.session_state.df_productos)
    
    else:
        mostrar_login()