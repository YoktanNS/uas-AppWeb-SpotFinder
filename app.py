import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="SpotFinder: Dashboard WiFi Gratis Indonesia",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Tema Gelap ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ffffff;
        text-align: center;
        padding: 1.5rem 0;
    }
    .sub-header {
        font-size: 1.25rem;
        color: #cccccc;
        text-align: center;
        margin-bottom: 2rem;
    }
    [data-testid="stMetric"] {
        background-color: #2a2a3a;
        border: 1px solid #4a4a5a;
        border-radius: 10px;
        padding: 1.5rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem;
        color: #a0a0b0;
    }
    [data-testid="stMetricValue"] {
        font-size: 2.2rem;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)


# ==================
#  FUNGSI LOAD DATA 
@st.cache_data
def load_data(file_path='data_jakarta.csv'):
    try:
        df = pd.read_csv(
            file_path,
            encoding='utf-8-sig',
            sep=';',
            on_bad_lines='skip'
        )

        rename_map = {
            'latitude': 'lat',
            'longitude': 'lon',
            'kecamatan': 'district',
            'kelurahan': 'sub_district',
            'gedung': 'location_name',
            'kabupaten_kota': 'region'
        }
        df = df.rename(columns=rename_map)

        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')

        # -------------------------------
        # AUTO FIX LAT / LONG TERTUKAR

        wrong_lat = df[(df['lat'] > 10) | (df['lat'] < -10)]

        if len(wrong_lat) > 0:
            st.warning("Dataset terdeteksi memiliki koordinat lat/lon yang tertukar. Memperbaiki secara otomatis...")
            df['lat'], df['lon'] = df['lon'], df['lat']

        df.dropna(subset=['lat', 'lon', 'region', 'district', 'sub_district'], inplace=True)

        return df

    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return None


# ==============
# FUNGSI UTAMA
def main():
    st.markdown('<h1 class="main-header"> SpotFinder: Dashboard WiFi Gratis Indonesia</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Selamat datang di SpotFinder. Temukan WiFi Gratis di Sekitar anda (Saat ini hanya bisa di DKI Jakarta).</p>', unsafe_allow_html=True)

    df_main = load_data('data_jakarta.csv')

    if df_main is None:
        return

    # --- Filter Sidebar ---
    st.sidebar.header(" Filter Pencarian")

    df_filtered = df_main.copy()

    region_list = ['Semua Wilayah'] + sorted(df_main['region'].unique())
    selected_region = st.sidebar.selectbox("Pilih Wilayah:", region_list)
    if selected_region != 'Semua Wilayah':
        df_filtered = df_filtered[df_filtered['region'] == selected_region]

    district_list = ['Semua Kecamatan'] + sorted(df_filtered['district'].unique())
    selected_district = st.sidebar.selectbox("Pilih Kecamatan:", district_list)
    if selected_district != 'Semua Kecamatan':
        df_filtered = df_filtered[df_filtered['district'] == selected_district]

    sub_district_list = ['Semua Kelurahan'] + sorted(df_filtered['sub_district'].unique())
    selected_sub_district = st.sidebar.selectbox("Pilih Kelurahan:", sub_district_list)
    if selected_sub_district != 'Semua Kelurahan':
        df_filtered = df_filtered[df_filtered['sub_district'] == selected_sub_district]

    # --- Statistik ---
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    total_hotspot = len(df_filtered)

    top_sub_district = df_filtered['sub_district'].mode()[0] if total_hotspot else "N/A"
    top_district = df_filtered['district'].mode()[0] if total_hotspot else "N/A"

    col1.metric(" Total Hotspot", total_hotspot)
    col2.metric(" Kecamatan Teratas", top_district)
    col3.metric(" Kelurahan Teratas", top_sub_district)

    st.markdown("---")

    # ===============================
    # TAB MENU
    tab1, tab2, tab3 = st.tabs([" Peta Lokasi", " Analisis Data", " Data Mentah"])

    # =====================================================
    # TAB 1 — PETA FOLIUM
    with tab1:
        st.markdown("## 🗺️ Peta Lokasi Hotspot")

        if df_filtered.empty:
            st.warning("Tidak ada data sesuai filter.")
        else:
            map_center = [df_filtered['lat'].mean(), df_filtered['lon'].mean()]
            zoom_level = 15 if selected_sub_district != 'Semua Kelurahan' else 12

            # --- Inisialisasi MAP ---
            m = folium.Map(location=map_center, zoom_start=zoom_level, tiles="CartoDB positron")

            # --- Tambahkan Google Maps ---
            google_maps = folium.TileLayer(
                tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
                attr="Google Maps",
                name="Google Maps"
            )
            google_maps.add_to(m)

            # --- Marker Cluster ---
            marker_cluster = MarkerCluster().add_to(m)

            for _, row in df_filtered.iterrows():
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    popup=f"<b>{row['location_name']}</b><br>{row['sub_district']}",
                    icon=folium.Icon(color='blue', icon='wifi', prefix='fa')
                ).add_to(marker_cluster)

            folium.LayerControl().add_to(m)

            st_folium(m, width=1200, height=550)
            st.info(f"Menampilkan {total_hotspot} titik.")

    # =====================================================
    # TAB 2 — PLOTLY CHART
    with tab2:
        st.markdown("## 📊 Analisis Data")
        if not df_filtered.empty:
            colA, colB = st.columns(2)

            with colA:
                st.markdown("### Top 10 Kelurahan")
                sub_counts = df_filtered['sub_district'].value_counts().head(10)
                figA = px.bar(
                    x=sub_counts.values, y=sub_counts.index,
                    orientation='h',
                    labels={'x': 'Jumlah', 'y': 'Kelurahan'},
                    template='plotly_dark'
                )
                st.plotly_chart(figA, use_container_width=True)

            with colB:
                st.markdown("### Distribusi Kecamatan")
                dist_counts = df_filtered['district'].value_counts().head(10)
                figB = px.pie(
                    values=dist_counts.values,
                    names=dist_counts.index,
                    hole=0.4,
                    template='plotly_dark'
                )
                st.plotly_chart(figB, use_container_width=True)

    # =====================================================
    # TAB 3 — DATAFRAME
    with tab3:
        st.markdown("## 📋 Data Mentah")
        st.dataframe(df_filtered, use_container_width=True)

        st.download_button(
            " Download CSV",
            df_filtered.to_csv(index=False).encode('utf-8'),
            "jakwifi_filtered.csv",
            "text/csv"
        )


if __name__ == "__main__":
    main()
