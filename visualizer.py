import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px

# --- Configuración de página ---
st.set_page_config(layout="wide", page_title="Tracker de Precios")
st.title("📊 Monitor de Precios e Inflación")

# --- 1. Menú Principal: Elegir Tienda ---
st.sidebar.header("Configuración")
tienda_seleccionada = st.sidebar.radio("Seleccionar Tienda:", ["Duvet Home", "Mercado Libre"])

# --- LÓGICA PARA DUVET HOME ---
if tienda_seleccionada == "Duvet Home":
    try:
        conn = sqlite3.connect('mattress_prices.db')
        df = pd.read_sql_query("SELECT * FROM price_history", conn)
        conn.close()
        
        if not df.empty:
            df['date_scraped'] = pd.to_datetime(df['date_scraped'])
            df['Leyenda'] = df['product_name'] + ' (' + df['size'] + ')'
            
            # Filtros Duvet
            st.sidebar.subheader("Filtros Duvet")
            productos = st.sidebar.multiselect("Producto", df['product_name'].unique().tolist(), default=[])
            if not productos: productos = df['product_name'].unique().tolist()
            
            tamanos = st.sidebar.multiselect("Tamaño", df[df['product_name'].isin(productos)]['size'].unique().tolist(), default=[])
            if not tamanos: tamanos = df['size'].unique().tolist()
            
            datos_filtrados = df[(df['product_name'].isin(productos)) & (df['size'].isin(tamanos))].sort_values('date_scraped')
            
            st.subheader(f"Evolución en {tienda_seleccionada}")
            fig = px.line(datos_filtrados, x='date_scraped', y='discount_price', color='Leyenda', markers=True)
            fig.update_layout(yaxis_tickformat="$,.0f", yaxis_title="Precio Promocional (ARS)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("La base de datos de Duvet está vacía.")
    except sqlite3.OperationalError:
        st.error("No se encontró la base de datos 'mattress_prices.db'.")

# --- LÓGICA PARA MERCADO LIBRE ---
elif tienda_seleccionada == "Mercado Libre":
    try:
        conn = sqlite3.connect('mercadolibre_prices.db')
        df = pd.read_sql_query("SELECT * FROM ml_price_history", conn)
        conn.close()
        
        if not df.empty:
            df['date_scraped'] = pd.to_datetime(df['date_scraped'])
            
            # Filtros Mercado Libre (No hay "Tamaño" acá)
            st.sidebar.subheader("Filtros Mercado Libre")
            productos = st.sidebar.multiselect("Producto", df['product_name'].unique().tolist(), default=[])
            if not productos: productos = df['product_name'].unique().tolist()
            
            datos_filtrados = df[df['product_name'].isin(productos)].sort_values('date_scraped')
            
            # Resumen de Precios ML
            st.subheader("Resumen Actual (ML)")
            resumen = []
            for nombre, grupo in datos_filtrados.groupby('product_name'):
                precio_actual = grupo.iloc[-1]['price']
                resumen.append({'Producto': nombre, 'Precio Actual': f"${precio_actual:,.0f}".replace(",", ".")})
            
            st.dataframe(pd.DataFrame(resumen), use_container_width=True)

            # Gráfico ML
            st.subheader(f"Evolución en {tienda_seleccionada}")
            fig = px.line(datos_filtrados, x='date_scraped', y='price', color='product_name', markers=True)
            fig.update_layout(yaxis_tickformat="$,.0f", yaxis_title="Precio (ARS)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("La base de datos de Mercado Libre está vacía.")
    except sqlite3.OperationalError:
        st.error("No se encontró la base de datos 'mercadolibre_prices.db'.")