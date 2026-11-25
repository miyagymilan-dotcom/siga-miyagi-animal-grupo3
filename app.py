from datetime import date
import sqlite3
import pandas as pd
import streamlit as st


# Configuración general de la página de Streamlit
st.set_page_config(
    page_title="SIGA · MIYAGI ANIMALs",
    page_icon="🐾",
    layout="wide",
)


@st.cache_resource
def obtener_conexion():
    """Crea y reutiliza la conexión SQLite de forma segura para Streamlit."""
    conexion = sqlite3.connect("mi_sistema.db", check_same_thread=False)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def inicializar_base_datos(conexion):
    """Crea tablas, datos iniciales y vista solo si aún no existen."""
    cursor = conexion.cursor()

    # Crear tablas principales si no existen
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS proveedores (
            id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT
        );

        CREATE TABLE IF NOT EXISTS productos (
            id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad_medida TEXT NOT NULL,
            precio_unitario REAL NOT NULL,
            stock_minimo INTEGER NOT NULL DEFAULT 0,
            fecha_vencimiento TEXT
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),
            fecha TEXT NOT NULL,
            id_proveedor INTEGER,
            id_cliente INTEGER,

            FOREIGN KEY (id_producto) REFERENCES productos(id_producto),
            FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor),
            FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
        );
        """
    )

    # Insertar proveedores iniciales solo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM proveedores")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO proveedores (nombre, telefono) VALUES (?, ?)",
            [
                ("Laboratorio Vecol", "3004567812"),
                ("Laboratorios Erma", "3015678923"),
                ("Laboratorio Calier", "3026789134"),
                ("Elmplastic", "3037891245"),
            ],
        )

    # Insertar clientes iniciales solo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO clientes (nombre, telefono) VALUES (?, ?)",
            [
                ("Nutresa", "3104567821"),
                ("Huevos KIKE", "3115678932"),
                ("Cervalle", "3126789143"),
                ("La Sevillana", "3137891254"),
            ],
        )

    # Insertar productos iniciales solo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO productos
            (nombre, categoria, unidad_medida, precio_unitario, stock_minimo, fecha_vencimiento)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("Vecol Antibiótico 500 mg", "Antibiótico", "unidad", 18500, 10, "2027-06-30"),
                ("Calier Vacuna Triple Felina", "Vacuna", "dosis", 32000, 15, "2027-03-15"),
                ("Erma Desparasitante 10 ml", "Antiparasitario", "ml", 12500, 20, "2028-01-20"),
                ("Miyagi Vitaminas Veterinarias 100 ml", "Vitaminas y suplementos", "ml", 24000, 12, "2027-09-10"),
            ],
        )

    # Insertar movimientos iniciales solo si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM movimientos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO movimientos
            (id_producto, tipo, cantidad, fecha, id_proveedor)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "entrada", 50, "2026-09-01", 1),
                (2, "entrada", 40, "2026-09-01", 3),
                (3, "entrada", 60, "2026-09-02", 2),
                (4, "entrada", 35, "2026-09-03", 4),
            ],
        )

        cursor.executemany(
            """
            INSERT INTO movimientos
            (id_producto, tipo, cantidad, fecha, id_cliente)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "salida", 8, "2026-09-10", 1),
                (2, "salida", 5, "2026-09-11", 2),
                (3, "salida", 12, "2026-09-12", 3),
                (4, "salida", 7, "2026-09-13", 4),
            ],
        )

    # Crear la vista de inventario si no existe
    cursor.execute(
        """
        CREATE VIEW IF NOT EXISTS vw_inventario AS
        SELECT
            p.id_producto,
            p.nombre,
            p.categoria,
            p.stock_minimo,
            COALESCE(
                SUM(
                    CASE
                        WHEN m.tipo = 'entrada' THEN m.cantidad
                        WHEN m.tipo = 'salida' THEN -m.cantidad
                        ELSE 0
                    END
                ), 0
            ) AS stock
        FROM productos AS p
        LEFT JOIN movimientos AS m
            ON m.id_producto = p.id_producto
        GROUP BY
            p.id_producto,
            p.nombre,
            p.categoria,
            p.stock_minimo
        """
    )

    conexion.commit()


def ver(sql, conexion):
    """Ejecuta una consulta SQL y devuelve un DataFrame de pandas."""
    return pd.read_sql_query(sql, conexion)


def registrar_entrada(conexion, id_producto, cantidad, fecha=None, id_proveedor=None):
    """Registra una entrada de inventario manteniendo la validación y lógica original."""
    cursor = conexion.cursor()

    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
        return False, "La cantidad debe ser un número entero mayor que cero."

    cursor.execute(
        "SELECT nombre FROM productos WHERE id_producto = ?",
        (id_producto,),
    )
    producto = cursor.fetchone()

    if producto is None:
        return False, f"El producto con ID {id_producto} no existe."

    fecha = fecha or date.today().isoformat()

    try:
        cursor.execute(
            """
            INSERT INTO movimientos
                (id_producto, tipo, cantidad, fecha, id_proveedor)
            VALUES (?, 'entrada', ?, ?, ?)
            """,
            (id_producto, cantidad, fecha, id_proveedor),
        )
        conexion.commit()
        return True, f"Entrada registrada: {cantidad} unidades de {producto[0]}."
    except Exception as e:
        conexion.rollback()
        return False, f"Error al registrar la entrada: {e}"


def registrar_salida(conexion, id_producto, cantidad, fecha=None, id_cliente=None):
    """Registra una salida de inventario verificando stock disponible desde vw_inventario."""
    cursor = conexion.cursor()

    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
        return False, "La cantidad debe ser un número entero mayor que cero."

    try:
        cursor.execute(
            """
            SELECT nombre, stock
            FROM vw_inventario
            WHERE id_producto = ?
            """,
            (id_producto,),
        )
        producto = cursor.fetchone()

        if producto is None:
            return False, f"El producto con ID {id_producto} no existe."

        nombre, stock_actual = producto

        if cantidad > stock_actual:
            return False, (
                f"Stock insuficiente para {nombre}. "
                f"Disponible: {stock_actual}; solicitado: {cantidad}."
            )

        fecha = fecha or date.today().isoformat()

        cursor.execute(
            """
            INSERT INTO movimientos
                (id_producto, tipo, cantidad, fecha, id_cliente)
            VALUES (?, 'salida', ?, ?, ?)
            """,
            (id_producto, cantidad, fecha, id_cliente),
        )
        conexion.commit()
        return True, f"Salida registrada: {cantidad} unidades de {nombre}."
    except Exception as e:
        conexion.rollback()
        return False, f"Error al registrar la salida: {e}"


def consultar_inventario(conexion, categoria=None):
    """Consulta el inventario desde vw_inventario, opcionalmente filtrado por categoría."""
    try:
        if categoria is None:
            consulta = """
                SELECT id_producto, nombre, categoria, stock_minimo, stock
                FROM vw_inventario
                ORDER BY nombre
            """
            return ver(consulta, conexion)

        consulta = """
            SELECT id_producto, nombre, categoria, stock_minimo, stock
            FROM vw_inventario
            WHERE categoria = ?
            ORDER BY nombre
        """
        return pd.read_sql_query(consulta, conexion, params=(categoria,))
    except Exception as e:
        st.error(f"Error al consultar el inventario: {e}")
        return None


def alertas_stock_bajo(conexion, minimo=30):
    """Consulta los productos cuyo stock está por debajo del umbral indicado."""
    if not isinstance(minimo, int) or isinstance(minimo, bool) or minimo < 0:
        st.error("El mínimo debe ser un número entero mayor o igual a cero.")
        return None

    try:
        consulta = """
            SELECT id_producto, nombre, categoria, stock, stock_minimo
            FROM vw_inventario
            WHERE stock < ?
            ORDER BY stock ASC
        """
        return pd.read_sql_query(consulta, conexion, params=(minimo,))
    except Exception as e:
        st.error(f"Error al consultar las alertas: {e}")
        return None


def agregar_producto(
    conexion,
    nombre,
    categoria,
    unidad_medida,
    precio_unitario,
    stock_minimo,
    fecha_vencimiento=None,
):
    """Agrega un producto nuevo a la tabla productos tras validar sus campos."""
    cursor = conexion.cursor()

    if not all(
        isinstance(valor, str) and valor.strip()
        for valor in (nombre, categoria, unidad_medida)
    ):
        return False, "El nombre, la categoría y la unidad de medida son obligatorios."

    if (
        isinstance(precio_unitario, bool)
        or not isinstance(precio_unitario, (int, float))
        or precio_unitario <= 0
    ):
        return False, "El precio debe ser un número mayor que cero."

    if (
        not isinstance(stock_minimo, int)
        or isinstance(stock_minimo, bool)
        or stock_minimo < 0
    ):
        return False, "El stock mínimo debe ser un entero mayor o igual a cero."

    try:
        cursor.execute(
            """
            INSERT INTO productos
                (nombre, categoria, unidad_medida,
                 precio_unitario, stock_minimo, fecha_vencimiento)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                nombre.strip(),
                categoria.strip(),
                unidad_medida.strip(),
                precio_unitario,
                stock_minimo,
                fecha_vencimiento,
            ),
        )
        conexion.commit()
        return True, f"Producto '{nombre.strip()}' registrado correctamente."
    except Exception as e:
        conexion.rollback()
        return False, f"Error al registrar el producto: {e}"


def registrar_entradas_lote(conexion, items, fecha=None):
    """Registra varias entradas en una sola transacción; si falla una, revierte todas."""
    cursor = conexion.cursor()

    if not items:
        return False, "Debe proporcionar al menos una entrada."

    for item in items:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            return False, "Cada entrada debe tener (id_producto, cantidad)."

        id_producto, cantidad = item

        if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
            return False, "Todas las cantidades deben ser enteros mayores que cero."

        cursor.execute(
            "SELECT 1 FROM productos WHERE id_producto = ?",
            (id_producto,),
        )
        if cursor.fetchone() is None:
            return (
                False,
                f"El producto con ID {id_producto} no existe. No se registró ninguna entrada.",
            )

    fecha = fecha or date.today().isoformat()

    try:
        for id_producto, cantidad in items:
            cursor.execute(
                """
                INSERT INTO movimientos (id_producto, tipo, cantidad, fecha)
                VALUES (?, 'entrada', ?, ?)
                """,
                (id_producto, cantidad, fecha),
            )
        conexion.commit()
        return True, f"Se registraron correctamente {len(items)} entradas."
    except Exception as e:
        conexion.rollback()
        return False, f"Error en el lote. Se cancelaron las entradas: {e}"


def renderizar_inicio(df_inventario):
    """Muestra la pestaña Inicio con descripción y métricas generales."""
    st.subheader("SIGA · MIYAGI ANIMALs")
    st.write(
        "Sistema de gestión de inventario para la farmacia veterinaria MIYAGI ANIMALs. "
        "Permite controlar existencias, registrar movimientos de entrada y salida y monitorear alertas de stock."
    )

    total_productos = len(df_inventario)
    unidades_en_stock = int(df_inventario["stock"].sum()) if not df_inventario.empty else 0
    productos_bajo_minimo = (
        int((df_inventario["stock"] < df_inventario["stock_minimo"]).sum())
        if not df_inventario.empty
        else 0
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Número de productos", total_productos)
    col2.metric("Unidades en stock", unidades_en_stock)
    col3.metric("Productos con stock bajo", productos_bajo_minimo)


def renderizar_registrar_movimiento(conexion, df_inventario):
    """Muestra el formulario para registrar entradas o salidas seleccionando producto por nombre."""
    st.subheader("Registrar movimiento")

    if df_inventario.empty:
        st.warning("No hay productos registrados en el inventario.")
        return

    mapa_productos = dict(zip(df_inventario["nombre"], df_inventario["id_producto"]))
    nombres_productos = list(mapa_productos.keys())

    with st.form("form_movimiento"):
        nombre_seleccionado = st.selectbox("Producto", options=nombres_productos)
        tipo_movimiento = st.selectbox("Tipo de movimiento", options=["entrada", "salida"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)
        enviar = st.form_submit_button("Guardar movimiento")

    if enviar:
        id_producto = int(mapa_productos[nombre_seleccionado])
        cantidad_entera = int(cantidad)

        if tipo_movimiento == "entrada":
            ok, mensaje = registrar_entrada(conexion, id_producto, cantidad_entera)
        else:
            ok, mensaje = registrar_salida(conexion, id_producto, cantidad_entera)

        if ok:
            st.success(mensaje)
            st.rerun()
        else:
            st.error(mensaje)


def renderizar_inventario(conexion, df_inventario):
    """Muestra la tabla del inventario con filtro por categoría."""
    st.subheader("Inventario actual")

    if df_inventario.empty:
        st.info("No hay datos de inventario para mostrar.")
        return

    categorias = ["Todas"] + sorted(df_inventario["categoria"].dropna().unique().tolist())
    categoria_elegida = st.selectbox("Filtrar por categoría", options=categorias)

    if categoria_elegida == "Todas":
        df_filtrado = consultar_inventario(conexion)
    else:
        df_filtrado = consultar_inventario(conexion, categoria=categoria_elegida)

    st.dataframe(df_filtrado, use_container_width=True)


def renderizar_alertas(conexion, df_inventario):
    """Muestra alertas de stock bajo según un umbral ajustable y un gráfico de barras."""
    st.subheader("Alertas de stock bajo")

    if df_inventario.empty:
        st.info("No hay productos para evaluar alertas.")
        return

    max_stock = max(int(df_inventario["stock"].max()), 30)
    umbral_minimo = st.slider(
        "Selecciona el stock mínimo de referencia",
        min_value=0,
        max_value=max_stock,
        value=30,
        step=1,
    )

    df_alertas = alertas_stock_bajo(conexion, minimo=umbral_minimo)
    st.dataframe(df_alertas, use_container_width=True)

    if df_alertas is not None and not df_alertas.empty:
        df_grafico = df_alertas.set_index("nombre")[["stock"]]
        st.bar_chart(df_grafico)
    else:
        st.info("No hay productos por debajo del stock mínimo seleccionado.")


def main():
    """Función principal de la aplicación Streamlit."""
    conexion = obtener_conexion()
    inicializar_base_datos(conexion)

    df_inventario = consultar_inventario(conexion)
    if df_inventario is None:
        df_inventario = pd.DataFrame(
            columns=["id_producto", "nombre", "categoria", "stock_minimo", "stock"]
        )

    pestana_inicio, pestana_movimiento, pestana_inventario, pestana_alertas = st.tabs(
        ["Inicio", "Registrar movimiento", "Inventario", "Alertas"]
    )

    with pestana_inicio:
        renderizar_inicio(df_inventario)

    with pestana_movimiento:
        renderizar_registrar_movimiento(conexion, df_inventario)

    with pestana_inventario:
        renderizar_inventario(conexion, df_inventario)

    with pestana_alertas:
        renderizar_alertas(conexion, df_inventario)


if __name__ == "__main__":
    main()
