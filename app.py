import streamlit as st
import pandas as pd
from datetime import datetime
import time 

# --- 1. CONFIGURACION INICIAL ---
st.set_page_config(layout="wide", page_title="Gestor de Inventario")

# --- 2. GESTION DE DATOS (CARGAR Y GUARDAR) ---

def load_data():
    """
    Carga todos los archivos CSV (Productos, Movimientos, Usuarios).
    Maneja la creacion de archivos/columnas si no existen.
    """
    try:
        df_productos = pd.read_csv("Productos.csv", sep=";")
        df_movimientos = pd.read_csv("Movimientos.csv", sep=";")
    except FileNotFoundError:
        st.error("Error: No se encontraron los archivos 'Productos.csv' o 'Movimientos.csv'.")
        return None, None, None
    
    # Cargar usuarios o crear archivo por defecto
    try:
        df_usuarios = pd.read_csv("usuarios.csv", sep=";")
    except FileNotFoundError:
        st.info("Creando archivo 'usuarios.csv' por defecto...")
        default_users = {'email': ['admin@gestor.com'], 'password': ['admin'], 'rol': ['Admin']}
        df_usuarios = pd.DataFrame(default_users)
        df_usuarios.to_csv("usuarios.csv", sep=";", index=False)
        
    if "Motivo" not in df_movimientos.columns:
        df_movimientos["Motivo"] = ""
    df_movimientos["Motivo"] = df_movimientos["Motivo"].fillna("")
    
    # Limpiar nombres de columnas
    df_productos.columns = df_productos.columns.str.strip()
    df_movimientos.columns = df_movimientos.columns.str.strip()
    df_usuarios.columns = df_usuarios.columns.str.strip()
    
    # Conversion de Fechas
    try:
        df_productos["Fecha_Entrada"] = pd.to_datetime(df_productos["Fecha_Entrada"], dayfirst=True, errors='coerce').dt.normalize()
        df_productos["Fecha_Vencimiento"] = pd.to_datetime(df_productos["Fecha_Vencimiento"], dayfirst=True, errors='coerce').dt.normalize()
        df_movimientos["Fecha"] = pd.to_datetime(df_movimientos["Fecha"], dayfirst=True, errors='coerce').dt.normalize()
    except KeyError as e:
        st.error(f"Error: Falta una columna de fecha esencial: {e}")
        return None, None, None

    if "Descripcion" not in df_productos.columns:
        df_productos["Descripcion"] = ""
    df_productos["Descripcion"] = df_productos["Descripcion"].fillna("") 

    return df_productos, df_movimientos, df_usuarios

def save_data(df_productos, df_movimientos):
    """
    Guarda los DataFrames de vuelta a CSV.
    """
    date_format_string = "%d-%m-%Y"
    
    df_prod_save = df_productos.copy()
    df_mov_save = df_movimientos.copy()

    df_prod_save["Fecha_Entrada"] = df_prod_save["Fecha_Entrada"].dt.strftime(date_format_string)
    df_prod_save["Fecha_Vencimiento"] = df_prod_save["Fecha_Vencimiento"].apply(
        lambda x: x.strftime(date_format_string) if pd.notnull(x) else ""
    )
    
    df_mov_save["Fecha"] = df_mov_save["Fecha"].dt.strftime(date_format_string)
    
    if "Motivo" not in df_mov_save.columns:
        df_mov_save["Motivo"] = ""
    df_mov_save["Motivo"] = df_mov_save["Motivo"].fillna("")

    df_prod_save.to_csv("Productos.csv", sep=";", index=False)
    df_mov_save.to_csv("Movimientos.csv", sep=";", index=False)

def update_statuses(df_productos):
    """
    Calcula y actualiza las columnas de 'Estado (Stock)' y 'Estado (Vencimiento)'
    """
    if df_productos.empty:
        return df_productos

    today = pd.to_datetime(datetime.now().date())
    
    df_productos['Estado (Stock)'] = df_productos.apply(
        lambda row: "🔴 CRITICO" if row['Stock_Actual'] < row['Stock_Minimo'] 
                      else ("🟡 ADVERTENCIA" if row['Stock_Actual'] < (row['Stock_Minimo'] * 1.5) 
                            else "🟢 OPTIMO"),
        axis=1
    )
    
    df_productos['Fecha_Vencimiento'] = pd.to_datetime(df_productos['Fecha_Vencimiento']).dt.normalize()
    
    dias_para_vencer = (df_productos['Fecha_Vencimiento'] - today).dt.days
    
    df_productos['Estado (Vencimiento)'] = "🟢 OK"
    df_productos.loc[dias_para_vencer <= 7, 'Estado (Vencimiento)'] = "🟡 PROXIMO A VENCER"
    df_productos.loc[dias_para_vencer < 0, 'Estado (Vencimiento)'] = "🔴 VENCIDO"
    df_productos.loc[pd.isna(df_productos['Fecha_Vencimiento']), 'Estado (Vencimiento)'] = "⚪ N/A"
    
    return df_productos

# --- 3. FUNCIONES DE LAS PAGINAS ---

def mostrar_inventario(df_productos):
    st.header("Estado del Inventario")
    
    st.subheader("Alertas ⚠️")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Stock Critico/Advertencia")
        alert_stock = df_productos[df_productos['Estado (Stock)'].isin(["🔴 CRITICO", "🟡 ADVERTENCIA"])]
        st.dataframe(alert_stock[["Nombre", "Stock_Actual", "Stock_Minimo", "Estado (Stock)"]], use_container_width=True)

    with col2:
        st.write("Vencimiento Proximo/Vencido")
        alert_venc = df_productos[df_productos['Estado (Vencimiento)'].isin(["🔴 VENCIDO", "🟡 PROXIMO A VENCER"])]
        st.dataframe(alert_venc[["Nombre", "Fecha_Vencimiento", "Estado (Vencimiento)"]], use_container_width=True,
                         column_config={"Fecha_Vencimiento": st.column_config.DateColumn("Fecha Vencimiento", format="DD-MM-YYYY")})
    
    st.divider()
    st.subheader("Inventario Completo")
    
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        if "Categoria" in df_productos.columns and not df_productos["Categoria"].empty:
            categorias = ["Todas"] + sorted(list(df_productos["Categoria"].dropna().unique()))
        else:
            categorias = ["Todas"]
        cat_filter = st.selectbox("Filtrar por Categoria:", options=categorias)
    
    with col_f2:
        search_term = st.text_input("Buscar por Nombre:", placeholder="Ej: Leche Entera")

    df_display = df_productos.copy()
    if cat_filter != "Todas":
        df_display = df_display[df_display["Categoria"] == cat_filter]
    if search_term:
        df_display = df_display[df_display["Nombre"].str.contains(search_term, case=False)]

    st.dataframe(df_display, use_container_width=True,
                 column_config={
                     "Fecha_Entrada": st.column_config.DateColumn("Fecha Entrada", format="DD-MM-YYYY"),
                     "Fecha_Vencimiento": st.column_config.DateColumn("Fecha Vencimiento", format="DD-MM-YYYY"),
                     "Precio_Unitario": st.column_config.NumberColumn("Precio Unitario", format="$ %d")
                 })

def registrar_movimiento(df_productos, df_movimientos, product_map_name_to_id, product_map_id_to_name):
    st.header("Registrar Nuevo Movimiento")
    
    col_f1, col_form, col_f3 = st.columns([1, 2, 1])
    
    with col_form:
        
        tipo_movimiento = st.radio(
            "Tipo de Movimiento:", 
            ["Entrada", "Salida", "Ajuste"], 
            horizontal=True,
            key='tipo_movimiento'
        )
        
        with st.form("nuevo_movimiento_form"):
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                producto_nombre = st.selectbox(
                    "Producto:", 
                    options=df_productos["Nombre"]
                )
                responsable = st.text_input("Responsable:", placeholder="Ej: Vendedor1")
            
            with col_m2:
                if st.session_state.tipo_movimiento == "Ajuste":
                    cantidad = st.number_input("Cantidad (Positiva o Negativa):", step=1)
                else:
                    cantidad = st.number_input("Cantidad:", min_value=1, step=1)
                
                motivo = ""
                if st.session_state.tipo_movimiento == "Ajuste":
                    motivo = st.text_input("Motivo del Ajuste:", placeholder="Ej: Merma por rotura")

            submitted = st.form_submit_button("Registrar Movimiento")

        if submitted:
            if not responsable:
                st.warning("El campo 'Responsable' no puede estar vacio.")
            elif st.session_state.tipo_movimiento == "Ajuste" and not motivo:
                st.warning("Debe ingresar un motivo para el ajuste.")
            elif st.session_state.tipo_movimiento == "Ajuste" and cantidad == 0:
                st.warning("La cantidad del ajuste no puede ser cero.")
            else:
                codigo_producto = product_map_name_to_id[producto_nombre]
                fecha_actual = pd.to_datetime(datetime.now().date())
                
                idx = df_productos.index[df_productos['Codigo'] == codigo_producto].tolist()[0]
                stock_actual = df_productos.at[idx, 'Stock_Actual']
                
                nuevo_stock = stock_actual
                
                if tipo_movimiento == "Salida":
                    if cantidad > stock_actual:
                        st.error(f"Error: No hay stock suficiente. Stock actual: {stock_actual}")
                        return 
                    nuevo_stock = stock_actual - cantidad
                
                elif tipo_movimiento == "Entrada":
                    nuevo_stock = stock_actual + cantidad
                    st.session_state.df_productos.at[idx, 'Fecha_Entrada'] = fecha_actual
                
                elif tipo_movimiento == "Ajuste":
                    nuevo_stock = stock_actual + cantidad 

                with st.spinner("Registrando y guardando..."):
                    st.session_state.df_productos.at[idx, 'Stock_Actual'] = nuevo_stock
                    
                    nuevo_movimiento = pd.DataFrame({
                        "Fecha": [fecha_actual],
                        "Codigo_Producto": [codigo_producto],
                        "Tipo": [tipo_movimiento],
                        "Cantidad": [cantidad],
                        "Responsable": [responsable],
                        "Motivo": [motivo]
                    })
                    
                    st.session_state.df_movimientos = pd.concat(
                        [st.session_state.df_movimientos, nuevo_movimiento], 
                        ignore_index=True
                    )
                    
                    save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                    st.success(f"¡Movimiento '{tipo_movimiento}' de {cantidad} unidad(es) registrado!")
                    st.session_state.df_productos = update_statuses(st.session_state.df_productos)
                    time.sleep(1)
                    st.rerun()

    st.divider()
    st.header("Historial de Movimientos")
    
    df_historial = df_movimientos.copy()
    
    try:
        df_historial["Nombre Producto"] = df_historial["Codigo_Producto"].map(product_map_id_to_name)
        column_order = ["Fecha", "Nombre Producto", "Tipo", "Cantidad", "Motivo", "Responsable", "Codigo_Producto"]
        
        st.dataframe(
            df_historial[column_order].sort_values(by="Fecha", ascending=False), 
            use_container_width=True,
            column_config={ "Fecha": st.column_config.DateColumn("Fecha", format="DD-MM-YYYY") }
        )
    except KeyError as e:
        st.warning("No se pudo cargar el historial de movimientos.")

def anadir_nuevo_producto(df_productos):
    st.header("Anadir Nuevo Producto al Inventario")
    
    col1, col_form, col3 = st.columns([1, 2, 1])

    with col_form:
        st.subheader("Detalles del Nuevo Producto")
        sin_vencimiento = st.checkbox("Este producto no tiene vencimiento")

        if df_productos.empty or "Categoria" not in df_productos.columns:
            categorias_existentes = []
        else:
            categorias_existentes = sorted(list(df_productos["Categoria"].dropna().unique()))
        
        opcion_nueva = "+ Anadir Nueva Categoria"
        opciones_categoria = categorias_existentes + [opcion_nueva]

        categoria_seleccionada = st.selectbox(
            "Categoria:", 
            options=opciones_categoria,
            index=0,
            key='widget_cat_select'
        )

        nueva_categoria_nombre = ""
        if st.session_state.widget_cat_select == opcion_nueva:
            nueva_categoria_nombre = st.text_input(
                "Nombre de la Nueva Categoria:", 
                placeholder="Ej: Lacteos", 
                key='widget_cat_new_name'
            )
        else:
            if 'widget_cat_new_name' in st.session_state:
                st.session_state.widget_cat_new_name = ""

    with col_form.form("nuevo_producto_form"):
        nombre = st.text_input("Nombre del Producto:")
        descripcion = st.text_area("Descripcion (Opcional):", placeholder="Ej: Leche entera de 1 litro, marca...")
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            stock_inicial = st.number_input("Stock Inicial:", min_value=0, step=1)
        with col_s2:
            stock_minimo = st.number_input("Stock Minimo:", min_value=0, step=1)
        with col_s3:
            precio_unitario = st.number_input("Precio Unitario:", min_value=0, step=1)
        
        fecha_vencimiento = None
        if sin_vencimiento:
            pass
        else:
            fecha_vencimiento = st.date_input("Fecha de Vencimiento:", datetime.now())
        
        submitted = st.form_submit_button("Anadir Producto")

    if submitted:
        if not nombre:
            col_form.warning("El campo 'Nombre del Producto' no puede estar vacio.")
            return
        elif nombre in df_productos["Nombre"].values:
            col_form.warning("Error: Ya existe un producto con ese nombre.")
            return

        categoria_final = ""
        if st.session_state.widget_cat_select == opcion_nueva:
            categoria_final = st.session_state.widget_cat_new_name.strip()
        else:
            categoria_final = st.session_state.widget_cat_select
        
        if not categoria_final:
            col_form.warning("Por favor, selecciona una categoria o escribe el nombre de la nueva.")
            return 
        
        if st.session_state.widget_cat_select == opcion_nueva:
            categorias_existentes_lower = [cat.lower() for cat in categorias_existentes]
            if categoria_final.lower() in categorias_existentes_lower:
                col_form.warning(f"Error: La categoria '{categoria_final}' ya existe. Por favor, seleccionala de la lista.")
                return 
            
        with col_form:
            with st.spinner("Anadiendo producto..."):
                
                if df_productos.empty:
                    nuevo_codigo = 1
                else:
                    nuevo_codigo = df_productos['Codigo'].max() + 1
                
                fecha_venc_final = pd.NaT if sin_vencimiento else pd.to_datetime(fecha_vencimiento)
                fecha_entrada = pd.to_datetime(datetime.now().date())
                
                nuevo_producto = pd.DataFrame({
                    "Codigo": [nuevo_codigo],
                    "Nombre": [nombre],
                    "Categoria": [categoria_final],
                    "Descripcion": [descripcion], 
                    "Stock_Inicial": [stock_inicial],
                    "Stock_Actual": [stock_inicial],
                    "Stock_Minimo": [stock_minimo],
                    "Fecha_Entrada": [fecha_entrada],
                    "Fecha_Vencimiento": [fecha_venc_final],
                    "Precio_Unitario": [precio_unitario]
                })
                
                st.session_state.df_productos, nuevo_producto = st.session_state.df_productos.align(nuevo_producto, join='outer', axis=1, fill_value="")
                
                st.session_state.df_productos = pd.concat(
                    [st.session_state.df_productos, nuevo_producto],
                    ignore_index=True
                ).fillna("") 
                
                save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                
                st.success(f"¡Producto '{nombre}' (Codigo: {nuevo_codigo}) anadido con exito!")
                time.sleep(2)
                st.rerun()

def gestionar_productos(df_productos):
    st.header("Gestionar Productos Existentes")

    if df_productos.empty:
        st.warning("No hay productos en el inventario para gestionar.")
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
            st.error("Error: No se pudo encontrar el producto. Por favor, refresca la pagina.")
            st.session_state.producto_seleccionado = ""
            st.rerun()
            return

        st.subheader(f"Editando: {nombre_producto}")
        
        categorias_existentes = sorted(list(df_productos["Categoria"].dropna().unique()))
        opcion_nueva = "+ Anadir Nueva Categoria"
        opciones_categoria = categorias_existentes + [opcion_nueva]
        
        try:
            current_cat_index = opciones_categoria.index(producto_data["Categoria"])
        except ValueError:
            current_cat_index = 0 
        
        categoria_seleccionada = st.selectbox(
            "Categoria:", 
            options=opciones_categoria,
            index=current_cat_index,
            key='widget_cat_editar_select'
        )
        
        nueva_categoria_nombre = ""
        if st.session_state.widget_cat_editar_select == opcion_nueva:
            nueva_categoria_nombre = st.text_input(
                "Nombre de la Nueva Categoria:", 
                placeholder="Ej: Lacteos",
                key='widget_cat_editar_new_name'
            )
        else:
            if 'widget_cat_editar_new_name' in st.session_state:
                st.session_state.widget_cat_editar_new_name = ""
            
        with st.form("editar_producto_form"):
            descripcion_actual = producto_data.get("Descripcion", "")
            descripcion = st.text_area("Descripcion (Opcional):", value=descripcion_actual)
            stock_minimo = st.number_input("Stock Minimo:", min_value=0, step=1, value=int(producto_data["Stock_Minimo"]))
            precio_unitario = st.number_input("Precio Unitario:", min_value=0, step=1, value=int(producto_data["Precio_Unitario"]))
            
            submitted_edit = st.form_submit_button("Guardar Cambios")

        if submitted_edit:
            
            categoria_final = ""
            if st.session_state.widget_cat_editar_select == opcion_nueva:
                categoria_final = st.session_state.widget_cat_editar_new_name.strip()
            else:
                categoria_final = st.session_state.widget_cat_editar_select

            if not categoria_final:
                st.warning("Por favor, selecciona una categoria o escribe el nombre de la nueva.")
                return

            if st.session_state.widget_cat_editar_select == opcion_nueva:
                categorias_existentes_lower = [cat.lower() for cat in categorias_existentes]
                if categoria_final.lower() in categorias_existentes_lower:
                    st.warning(f"Error: La categoria '{categoria_final}' ya existe. Por favor, seleccionala de la lista.")
                    return 
                
            with st.spinner("Guardando cambios..."):
                st.session_state.df_productos.at[idx, "Descripcion"] = descripcion
                st.session_state.df_productos.at[idx, "Categoria"] = categoria_final
                st.session_state.df_productos.at[idx, "Stock_Minimo"] = stock_minimo
                st.session_state.df_productos.at[idx, "Precio_Unitario"] = precio_unitario
                
                save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                st.success(f"¡Producto '{nombre_producto}' actualizado con exito!")
                time.sleep(1)
                st.rerun()

        st.divider()
        st.subheader("Zona de Peligro: Eliminar Producto")
        st.warning(f"Advertencia: Estas a punto de eliminar '{nombre_producto}' permanentemente. Esta accion no se puede deshacer.")
        
        confirm_delete = st.checkbox("Si, estoy seguro de que quiero eliminar este producto.")
        
        if st.button("Eliminar Producto Permanentemente", disabled=not confirm_delete, type="primary"):
            with st.spinner("Eliminando producto..."):
                st.session_state.df_productos = st.session_state.df_productos.drop(index=idx).reset_index(drop=True)
                
                save_data(st.session_state.df_productos, st.session_state.df_movimientos)
                st.success(f"¡Producto '{nombre_producto}' eliminado con exito!")
                
                st.session_state.producto_seleccionado = ""
                time.sleep(2)
                st.rerun()

def mostrar_login(df_usuarios):
    col1, col_form, col3 = st.columns([1, 2, 1])

    with col_form:
        st.title("Gestor de Inventario")
        st.subheader("Por favor, inicie sesion para continuar")
        
        with st.form("login_form"):
            email = st.text_input("Correo Electronico", placeholder="ejemplo@correo.com")
            password = st.text_input("Contrasena", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar")
            
            if submitted:
                if not email or not password:
                    st.warning("Por favor, ingresa tu correo y contrasena.")
                else:
                    usuario_encontrado = df_usuarios[
                        (df_usuarios["email"] == email) & (df_usuarios["password"] == password)
                    ]
                    
                    if not usuario_encontrado.empty:
                        st.session_state.logged_in = True
                        st.session_state.email = usuario_encontrado.iloc[0]["email"]
                        st.session_state.rol = usuario_encontrado.iloc[0]["rol"]
                        st.rerun()
                    else:
                        st.error("Email o contrasena incorrectos.")

    st.divider()
    st.caption("© 2024 - Equipo Gestor. Todos los derechos reservados.")


# --- 4. CODIGO PRINCIPAL (MODIFICADO CON LOGICA DE LOGIN Y ROLES) ---

if 'data_loaded' not in st.session_state:
    df_productos, df_movimientos, df_usuarios = load_data()
    if df_productos is not None:
        st.session_state.df_productos = df_productos
        st.session_state.df_movimientos = df_movimientos
        st.session_state.df_usuarios = df_usuarios 
        st.session_state.data_loaded = True
        st.session_state.logged_in = False 
        st.session_state.rol = None 
        st.session_state.email = None 
    
if 'data_loaded' in st.session_state:
    
    if st.session_state.logged_in:
        
        st.session_state.df_productos = update_statuses(st.session_state.df_productos)

        product_map_name_to_id = dict(zip(st.session_state.df_productos['Nombre'], st.session_state.df_productos['Codigo']))
        product_map_id_to_name = dict(zip(st.session_state.df_productos['Codigo'], st.session_state.df_productos['Nombre']))

        st.title("Gestor de Inventario")

        with st.sidebar:
            st.header("Navegacion")
            
            st.caption(f"Usuario: {st.session_state.email}")
            st.caption(f"Rol: {st.session_state.rol}")
            st.divider()

            menu_base = ["Inventario Actual", "Registrar Movimiento"]
            menu_admin = ["Anadir Nuevo Producto", "Gestionar Productos"]
            
            if st.session_state.rol == "Admin":
                menu_options = menu_base + menu_admin
            else: 
                menu_options = menu_base
            
            if 'page' not in st.session_state or st.session_state.page not in menu_options:
                st.session_state.page = "Inventario Actual"
            
            # --- ARREGLO DOBLE CLIC ---
            def update_page_state():
                st.session_state.page = st.session_state.menu_radio
            
            current_page_index = menu_options.index(st.session_state.page)
            
            page = st.radio(
                "Selecciona una pagina:",
                menu_options,
                index=current_page_index,
                key="menu_radio", 
                on_change=update_page_state
            )
            # --- FIN ARREGLO ---
            
            st.divider()
            
            if st.button("Cerrar Sesion"):
                st.session_state.logged_in = False
                st.session_state.rol = None
                st.session_state.email = None
                st.rerun()

        if st.session_state.page == "Inventario Actual":
            mostrar_inventario(st.session_state.df_productos)
            
        elif st.session_state.page == "Registrar Movimiento":
            registrar_movimiento(
                st.session_state.df_productos, 
                st.session_state.df_movimientos,
                product_map_name_to_id, 
                product_map_id_to_name
            )
            
        elif st.session_state.page == "Anadir Nuevo Producto":
            anadir_nuevo_producto(st.session_state.df_productos)
        
        elif st.session_state.page == "Gestionar Productos":
            gestionar_productos(st.session_state.df_productos)
    
    else:
        mostrar_login(st.session_state.df_usuarios)