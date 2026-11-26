import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SIGA · MIYAGI ANIMALs",
    page_icon="🐾",
    layout="wide",
)


@st.cache_resource
def get_connection():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    inicializar_bd(conn)
    return conn


def inicializar_bd(conn):
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS proveedores (
            id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            ciudad TEXT
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            ciudad TEXT
        );

        CREATE TABLE IF NOT EXISTS productos (
            id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_medida TEXT NOT NULL,
            precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
            stock_minimo INTEGER NOT NULL CHECK (stock_minimo >= 0),
            fecha_vencimiento TEXT
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL,
            id_proveedor INTEGER,
            id_cliente INTEGER,
            tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            fecha TEXT NOT NULL,
            observacion TEXT,
            FOREIGN KEY (id_producto) REFERENCES productos(id_producto),
            FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor),
            FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
        );

        DROP VIEW IF EXISTS vw_inventario;
        CREATE VIEW vw_inventario AS
        SELECT
            p.id_producto,
            p.nombre,
            p.categoria,
            p.unidad_medida,
            p.precio_unitario,
            p.stock_minimo,
            p.fecha_vencimiento,
            COALESCE(
                SUM(
                    CASE
                        WHEN m.tipo = 'entrada' THEN m.cantidad
                        WHEN m.tipo = 'salida' THEN -m.cantidad
                        ELSE 0
                    END
                ),
                0
            ) AS stock
        FROM productos p
        LEFT JOIN movimientos m ON p.id_producto = m.id_producto
        GROUP BY
            p.id_producto,
            p.nombre,
            p.categoria,
            p.unidad_medida,
            p.precio_unitario,
            p.stock_minimo,
            p.fecha_vencimiento;
        """
    )

    # Datos iniciales de ejemplo si la base está vacía
    existe = cursor.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    if existe == 0:
        proveedores_ini = [
            ("VetPharma Colombia", "3104567890", "Bogotá"),
            ("BioAnimal Distribución", "3157891234", "Medellín"),
            ("AgroSalud Veterinaria", "3209876543", "Cali"),
        ]
        cursor.executemany(
            "INSERT INTO proveedores (nombre, telefono, ciudad) VALUES (?, ?, ?)",
            proveedores_ini,
        )

        clientes_ini = [
            ("Nutresa", "6043214567", "Medellín"),
            ("Huevos KIKE", "6024457890", "Cali"),
            ("Cervalle", "6025568901", "Cali"),
            ("La Sevillana", "3126789012", "Palmira"),
        ]
        cursor.executemany(
            "INSERT INTO clientes (nombre, telefono, ciudad) VALUES (?, ?, ?)",
            clientes_ini,
        )

        productos_ini = [
            ("Ivermectina 1% 50ml", "Antiparasitarios", "frasco", 28500, 15, "2027-06-30"),
            ("Amoxicilina Vet 250mg", "Antibióticos", "caja", 34000, 12, "2027-03-15"),
            ("Vacuna Polivalente Canina", "Biológicos", "dosis", 42000, 20, "2026-12-31"),
            ("Complejo B Inyectable 100ml", "Vitaminas y Suplementos", "frasco", 23000, 10, "2027-09-20"),
            ("Meloxicam Oral 15ml", "Antiinflamatorios", "frasco", 19500, 10, "2027-05-10"),
            ("Clorhexidina Spray 120ml", "Antisépticos", "frasco", 16000, 8, "2027-08-01"),
        ]
        cursor.executemany(
            """
            INSERT INTO productos
            (nombre, categoria, unidad_medida, precio_unitario, stock_minimo, fecha_vencimiento)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            productos_ini,
        )

        hoy = date.today().isoformat()
        movimientos_ini = [
            (1, 1, None, "entrada", 35, hoy, "Compra inicial lote A"),
            (2, 1, None, "entrada", 25, hoy, "Reposición mensual"),
            (3, 2, None, "entrada", 30, hoy, "Cadena de frío verificada"),
            (4, 2, None, "entrada", 18, hoy, "Ingreso proveedor"),
            (5, 3, None, "entrada", 14, hoy, "Ingreso inicial"),
            (6, 3, None, "entrada", 20, hoy, "Ingreso inicial"),
            (1, None, 1, "salida", 12, hoy, "Despacho pedido Nutresa"),
            (3, None, 2, "salida", 16, hoy, "Entrega clínica Huevos KIKE"),
            (5, None, 3, "salida", 8, hoy, "Pedido Cervalle"),
        ]
        cursor.executemany(
            """
            INSERT INTO movimientos
            (id_producto, id_proveedor, id_cliente, tipo, cantidad, fecha, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            movimientos_ini,
        )
        conn.commit()


# --- Funciones de negocio (SQLite) ---

def obtener_productos(conn):
    return pd.read_sql_query("SELECT * FROM vw_inventario ORDER BY nombre", conn)


def obtener_proveedores(conn):
    return pd.read_sql_query("SELECT * FROM proveedores ORDER BY nombre", conn)


def obtener_clientes(conn):
    return pd.read_sql_query("SELECT * FROM clientes ORDER BY nombre", conn)


def obtener_historial_movimientos(conn):
    query = """
    SELECT
        m.id_movimiento AS ID,
        m.fecha AS Fecha,
        UPPER(m.tipo) AS Tipo,
        p.nombre AS Producto,
        m.cantidad AS Cantidad,
        COALESCE(pr.nombre, cl.nombre, '—') AS Tercero,
        COALESCE(m.observacion, '') AS Observacion
    FROM movimientos m
    JOIN productos p ON m.id_producto = p.id_producto
    LEFT JOIN proveedores pr ON m.id_proveedor = pr.id_proveedor
    LEFT JOIN clientes cl ON m.id_cliente = cl.id_cliente
    ORDER BY m.id_movimiento DESC
    LIMIT 20
    """
    return pd.read_sql_query(query, conn)


def agregar_proveedor(conn, nombre, telefono, ciudad):
    nombre = nombre.strip()
    if not nombre:
        return False, "El nombre del proveedor es obligatorio."
    try:
        conn.execute(
            "INSERT INTO proveedores (nombre, telefono, ciudad) VALUES (?, ?, ?)",
            (nombre, telefono.strip(), ciudad.strip()),
        )
        conn.commit()
        return True, f"Proveedor '{nombre}' registrado correctamente."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Error al guardar proveedor: {e}"


def agregar_cliente(conn, nombre, telefono, ciudad):
    nombre = nombre.strip()
    if not nombre:
        return False, "El nombre del cliente es obligatorio."
    try:
        conn.execute(
            "INSERT INTO clientes (nombre, telefono, ciudad) VALUES (?, ?, ?)",
            (nombre, telefono.strip(), ciudad.strip()),
        )
        conn.commit()
        return True, f"Cliente '{nombre}' registrado correctamente."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Error al guardar cliente: {e}"


def agregar_producto(conn, nombre, categoria, unidad_medida, precio_unitario, stock_minimo, fecha_vencimiento):
    nombre = nombre.strip()
    if not nombre:
        return False, "El nombre del producto es obligatorio."
    try:
        conn.execute(
            """
            INSERT INTO productos
            (nombre, categoria, unidad_medida, precio_unitario, stock_minimo, fecha_vencimiento)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                nombre,
                categoria.strip(),
                unidad_medida.strip(),
                float(precio_unitario),
                int(stock_minimo),
                str(fecha_vencimiento),
            ),
        )
        conn.commit()
        return True, f"Producto '{nombre}' agregado al catálogo."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Error al agregar producto: {e}"


def registrar_entrada(conn, id_producto, id_proveedor, cantidad, observacion=""):
    if cantidad <= 0:
        return False, "La cantidad debe ser mayor que cero."
    try:
        prod = conn.execute(
            "SELECT nombre FROM productos WHERE id_producto = ?", (id_producto,)
        ).fetchone()
        prov = conn.execute(
            "SELECT nombre FROM proveedores WHERE id_proveedor = ?", (id_proveedor,)
        ).fetchone()
        if not prod or not prov:
            return False, "Producto o proveedor no válido."

        conn.execute(
            """
            INSERT INTO movimientos (id_producto, id_proveedor, id_cliente, tipo, cantidad, fecha, observacion)
            VALUES (?, ?, NULL, 'entrada', ?, ?, ?)
            """,
            (id_producto, id_proveedor, int(cantidad), date.today().isoformat(), observacion.strip()),
        )
        conn.commit()
        return True, f"Entrada registrada: +{cantidad} unid. de '{prod['nombre']}' (Proveedor: {prov['nombre']})."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Error en la base de datos: {e}"


def registrar_salida(conn, id_producto, id_cliente, cantidad, observacion=""):
    if cantidad <= 0:
        return False, "La cantidad debe ser mayor que cero."
    try:
        fila = conn.execute(
            "SELECT nombre, stock FROM vw_inventario WHERE id_producto = ?", (id_producto,)
        ).fetchone()
        cli = conn.execute(
            "SELECT nombre FROM clientes WHERE id_cliente = ?", (id_cliente,)
        ).fetchone()
        if not fila or not cli:
            return False, "Producto o cliente no válido."

        stock_actual = int(fila["stock"])
        if cantidad > stock_actual:
            return (
                False,
                f"Stock insuficiente para '{fila['nombre']}'. Disponible: {stock_actual}, solicitado: {cantidad}.",
            )

        conn.execute(
            """
            INSERT INTO movimientos (id_producto, id_proveedor, id_cliente, tipo, cantidad, fecha, observacion)
            VALUES (?, NULL, ?, 'salida', ?, ?, ?)
            """,
            (id_producto, id_cliente, int(cantidad), date.today().isoformat(), observacion.strip()),
        )
        conn.commit()
        return True, f"Salida registrada: -{cantidad} unid. de '{fila['nombre']}' para cliente '{cli['nombre']}'."
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Error en la base de datos: {e}"


# --- Interfaz Streamlit ---

def main():
    conn = get_connection()

    st.title("🐾 SIGA · MIYAGI ANIMALs")
    st.caption("Sistema de Gestión de Inventario Veterinario · Entradas, Salidas, Stock y Alertas")
    st.divider()

    tab_inicio, tab_movimientos, tab_inventario, tab_alertas = st.tabs(
        ["Inicio", "Registrar movimiento", "Inventario", "Alertas"]
    )

    # TAB 1: INICIO
    with tab_inicio:
        df_inv = obtener_productos(conn)
        df_prov = obtener_proveedores(conn)
        df_cli = obtener_clientes(conn)

        total_productos = len(df_inv)
        total_unidades = int(df_inv["stock"].sum()) if not df_inv.empty else 0
        bajo_stock = int((df_inv["stock"] <= df_inv["stock_minimo"]).sum()) if not df_inv.empty else 0
        valor_inventario = float((df_inv["stock"] * df_inv["precio_unitario"]).sum()) if not df_inv.empty else 0.0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            with st.container(border=True):
                st.metric("Productos activos", total_productos)
        with c2:
            with st.container(border=True):
                st.metric("Unidades en stock", total_unidades)
        with c3:
            with st.container(border=True):
                st.metric("Alertas stock bajo", bajo_stock)
        with c4:
            with st.container(border=True):
                st.metric("Valor estimado", f"${valor_inventario:,.0f}")

        col_izq, col_der = st.columns([2, 1])
        with col_izq:
            with st.container(border=True):
                st.subheader("Últimos movimientos registrados")
                df_hist = obtener_historial_movimientos(conn)
                st.dataframe(df_hist, use_container_width=True, hide_index=True)

        with col_der:
            with st.container(border=True):
                st.subheader("Directorio activo")
                st.write(f"**Proveedores registrados:** {len(df_prov)}")
                st.dataframe(df_prov[["nombre", "ciudad"]], use_container_width=True, hide_index=True)
                st.write(f"**Clientes registrados:** {len(df_cli)}")
                st.dataframe(df_cli[["nombre", "ciudad"]], use_container_width=True, hide_index=True)

    # TAB 2: REGISTRAR MOVIMIENTO (Entradas con Proveedor, Salidas con Cliente y Altas rápidas)
    with tab_movimientos:
        st.subheader("Gestión de Entradas, Salidas y Catálogo")

        df_inv = obtener_productos(conn)
        df_prov = obtener_proveedores(conn)
        df_cli = obtener_clientes(conn)

        mapa_productos = {
            f"{row['nombre']} (Stock: {row['stock']} {row['unidad_medida']})": int(row["id_producto"])
            for _, row in df_inv.iterrows()
        }
        mapa_proveedores = {
            f"{row['nombre']} ({row['ciudad']})": int(row["id_proveedor"])
            for _, row in df_prov.iterrows()
        }
        mapa_clientes = {
            f"{row['nombre']} ({row['ciudad']})": int(row["id_cliente"])
            for _, row in df_cli.iterrows()
        }

        col_ent, col_sal = st.columns(2)

        # Bloque 1: Registrar ENTRADA con Proveedor
        with col_ent:
            with st.container(border=True):
                st.markdown("### 📥 Registrar Entrada (Proveedor)")
                st.caption("Ingresa mercancía al inventario asociando el proveedor que entrega.")
                with st.form("form_entrada", clear_on_submit=True):
                    prod_ent_label = st.selectbox("Producto", list(mapa_productos.keys()), key="sel_prod_ent")
                    prov_label = st.selectbox("Proveedor", list(mapa_proveedores.keys()), key="sel_prov")
                    cant_ent = st.number_input("Cantidad que ingresa", min_value=1, step=1, value=5, key="cant_ent")
                    obs_ent = st.text_input("Observación / Lote (opcional)", key="obs_ent")
                    sub_ent = st.form_submit_button("Guardar entrada", type="primary", use_container_width=True)

                    if sub_ent:
                        ok, msg = registrar_entrada(
                            conn,
                            mapa_productos[prod_ent_label],
                            mapa_proveedores[prov_label],
                            int(cant_ent),
                            obs_ent,
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        # Bloque 2: Registrar SALIDA con Cliente
        with col_sal:
            with st.container(border=True):
                st.markdown("### 📤 Registrar Salida (Cliente)")
                st.caption("Despacha productos validando existencias y registrando el cliente que compra.")
                with st.form("form_salida", clear_on_submit=True):
                    prod_sal_label = st.selectbox("Producto", list(mapa_productos.keys()), key="sel_prod_sal")
                    cli_label = st.selectbox("Cliente que compra", list(mapa_clientes.keys()), key="sel_cli")
                    cant_sal = st.number_input("Cantidad que sale", min_value=1, step=1, value=2, key="cant_sal")
                    obs_sal = st.text_input("Observación / Pedido (opcional)", key="obs_sal")
                    sub_sal = st.form_submit_button("Guardar salida", type="primary", use_container_width=True)

                    if sub_sal:
                        ok, msg = registrar_salida(
                            conn,
                            mapa_productos[prod_sal_label],
                            mapa_clientes[cli_label],
                            int(cant_sal),
                            obs_sal,
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        st.divider()
        st.markdown("### ➕ Crear nuevo Proveedor, Producto o Cliente")
        col_np, col_nprod, col_ncli = st.columns(3)

        with col_np:
            with st.container(border=True):
                st.markdown("**Nuevo Proveedor**")
                with st.form("form_nuevo_prov", clear_on_submit=True):
                    p_nom = st.text_input("Nombre empresa / proveedor")
                    p_tel = st.text_input("Teléfono")
                    p_ciu = st.text_input("Ciudad", value="Cali")
                    if st.form_submit_button("Agregar proveedor", use_container_width=True):
                        ok, msg = agregar_proveedor(conn, p_nom, p_tel, p_ciu)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        with col_nprod:
            with st.container(border=True):
                st.markdown("**Nuevo Producto**")
                with st.form("form_nuevo_prod", clear_on_submit=True):
                    pr_nom = st.text_input("Nombre del producto")
                    pr_cat = st.selectbox(
                        "Categoría",
                        [
                            "Antiparasitarios",
                            "Antibióticos",
                            "Biológicos",
                            "Vitaminas y Suplementos",
                            "Antiinflamatorios",
                            "Antisépticos",
                        ],
                    )
                    pr_uni = st.selectbox("Unidad de medida", ["frasco", "caja", "dosis", "unidad", "sobre"])
                    pr_pre = st.number_input("Precio unitario ($)", min_value=0, step=1000, value=20000)
                    pr_min = st.number_input("Stock mínimo", min_value=1, step=1, value=10)
                    pr_ven = st.date_input("Fecha de vencimiento", value=date(2027, 6, 30))
                    if st.form_submit_button("Agregar producto", use_container_width=True):
                        ok, msg = agregar_producto(conn, pr_nom, pr_cat, pr_uni, pr_pre, pr_min, pr_ven)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

        with col_ncli:
            with st.container(border=True):
                st.markdown("**Nuevo Cliente**")
                with st.form("form_nuevo_cli", clear_on_submit=True):
                    c_nom = st.text_input("Nombre del cliente / clínica")
                    c_tel = st.text_input("Teléfono contacto")
                    c_ciu = st.text_input("Ciudad cliente", value="Cali")
                    if st.form_submit_button("Agregar cliente", use_container_width=True):
                        ok, msg = agregar_cliente(conn, c_nom, c_tel, c_ciu)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    # TAB 3: INVENTARIO
    with tab_inventario:
        st.subheader("Inventario actual (calculado desde vw_inventario)")
        df_inv = obtener_productos(conn)

        categorias = ["Todas"] + sorted(df_inv["categoria"].unique().tolist())
        cat_sel = st.selectbox("Filtrar por categoría", categorias)

        if cat_sel != "Todas":
            df_mostrar = df_inv[df_inv["categoria"] == cat_sel].copy()
        else:
            df_mostrar = df_inv.copy()

        st.dataframe(
            df_mostrar,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id_producto": "ID",
                "nombre": "Producto",
                "categoria": "Categoría",
                "unidad_medida": "Unidad",
                "precio_unitario": st.column_config.NumberColumn("Precio Unit.", format="$%d"),
                "stock_minimo": "Stock Mínimo",
                "fecha_vencimiento": "Vencimiento",
                "stock": "Stock Actual",
            },
        )

    # TAB 4: ALERTAS
    with tab_alertas:
        st.subheader("Alertas de reposición y stock bajo")
        df_inv = obtener_productos(conn)

        umbral = st.slider(
            "Mostrar productos con stock menor o igual a:",
            min_value=1,
            max_value=50,
            value=15,
        )

        df_alertas = df_inv[df_inv["stock"] <= umbral].sort_values("stock")

        if df_alertas.empty:
            st.success(f"No hay productos con stock menor o igual a {umbral} unidades.")
        else:
            st.warning(f"Se encontraron {len(df_alertas)} producto(s) que requieren atención.")
            col_t, col_g = st.columns([1.2, 1])
            with col_t:
                st.dataframe(
                    df_alertas[["nombre", "categoria", "stock", "stock_minimo"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "nombre": "Producto",
                        "categoria": "Categoría",
                        "stock": "Stock Actual",
                        "stock_minimo": "Mínimo Requerido",
                    },
                )
            with col_g:
                st.bar_chart(df_alertas.set_index("nombre")["stock"])

    st.divider()
    st.caption("SIGA · MIYAGI ANIMALs · Grupo 3 · Programación 2")


if __name__ == "__main__":
    main()