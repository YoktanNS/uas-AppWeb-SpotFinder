import streamlit as st
import pandas as pd
import pydeck as pdk  # <--- Library Peta BARU
import plotly.express as px

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="JakWifi-View - Dasbor WiFi Publik Jakarta",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Kustom untuk Tampilan Gelap ---
st.markdown("""
<style>
    /* Menggunakan tema gelap bawaan Streamlit sebagai dasar */
    .main-header {
        font-size: 2.5rem; /* Sedikit lebih kecil agar pas */
        font-weight: bold;
        color: #ffffff; /* Putih untuk tema gelap */
        text-align: center;
        padding: 1.5rem 0;
    }
    .sub-header {
        font-size: 1.25rem;
        color: #cccccc; /* Abu-abu muda */
        text-align: center;
        margin-bottom: 2rem;
    }
    /* Kustomisasi stMetric */
    [data-testid="stMetric"] {
        background-color: #2a2a3a; /* Latar belakang ungu gelap */
        border: 1px solid #4a4a5a;
        border-radius: 10px;
        padding: 1.5rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem;
        color: #a0a0b0; /* Warna label abu-abu */
    }
    [data-testid="stMetricValue"] {
        font-size: 2.2rem;
        color: #ffffff; /* Nilai putih */
    }
</style>
""", unsafe_allow_html=True)

# --- Fungsi Pemuatan Data (Sesuai Debug Anda) ---
@st.cache_data
def load_data(file_path='data_jakarta.csv'):
    """
    Memuat data dengan encoding dan nama kolom yang sudah benar.
    """
    try:
        df = pd.read_csv(
            file_path, 
            encoding='utf-8-sig', # Benar: dari debug (menangani BOM Excel)
            sep=';',           # Benar: dari debug (pemisah titik koma)
            on_bad_lines='skip'  # Melewati baris yang rusak
        )
        
        # --- BLOK RENAME (SESUAI DAFTAR KOLOM ANDA) ---
        rename_map = {
            'latitude': 'lat',           # Kolom 'latitude' ada
            'longitude': 'lon',        # Benar: 'longitude' (bukan w_longitude)
            'kecamatan': 'district',     # Kolom 'kecamatan' ada
            'kelurahan': 'sub_district', # Kolom 'kelurahan' ada
            'gedung': 'location_name', # Benar: 'gedung' sebagai nama lokasi
            'kabupaten_kota': 'region'   # Kolom 'kabupaten_kota' ada
        }
        
        # Cek dulu kolom yang diperlukan ada
        required_old_cols = list(rename_map.keys())
        missing_cols = [col for col in required_old_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Error Kritis: Kolom wajib berikut tidak ditemukan di CSV: {', '.join(missing_cols)}")
            st.info("Pastikan Anda menggunakan file 'Data Lokasi Wifi DKI Jakarta' yang benar.")
            return None

        # Jika semua ada, baru rename
        df = df.rename(columns=rename_map)

        # --- BLOK CLEANING (PEMBERSIHAN DATA) ---
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        
        # Memastikan kolom filter tidak kosong
        df.dropna(subset=['lat', 'lon', 'region', 'district', 'sub_district'], inplace=True)
        
        # Jangan tampilkan st.success di versi final
        # st.success("✅ Data berhasil dimuat!") 
        return df
    
    except FileNotFoundError:
        st.error(f"❌ File '{file_path}' tidak ditemukan. Pastikan ada di folder yang sama.")
        return None
    except Exception as e:
        st.error(f"❌ Gagal total memuat file. Error: {e}")
        return None

# --- Fungsi Utama Aplikasi ---
def main():
    # Header
    st.markdown('<h1 class="main-header">SpotFinder: Dasbor WiFi Publik Indonesia</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Selamat datang di SpotFinder. Temukan dan analisis Wifi Gratis di sekitar anda (saat ini hanya bisa di jakarta).</p>', unsafe_allow_html=True)
    
    # Memuat data
    df_main = load_data('data_jakarta.csv')
    
    if df_main is None:
        st.error("Aplikasi tidak dapat berjalan tanpa data. Silakan periksa file CSV Anda.")
        return # Hentikan eksekusi jika data gagal dimuat

    # --- Sidebar Filter (Filter Bertingkat) ---
    st.sidebar.header(" Filter Pencarian")

    df_filtered = df_main.copy() # Mulai dengan data penuh

    # Filter 1: Wilayah ('region' berasal dari 'kabupaten_kota')
    region_list = ['Semua Wilayah'] + sorted(list(df_main['region'].dropna().unique()))
    selected_region = st.sidebar.selectbox("Pilih Wilayah:", region_list)
    
    if selected_region != 'Semua Wilayah':
        df_filtered = df_main[df_main['region'] == selected_region]

    # Filter 2: Kecamatan (Dinamis berdasarkan Wilayah)
    district_list = ['Semua Kecamatan'] + sorted(list(df_filtered['district'].dropna().unique()))
    selected_district = st.sidebar.selectbox("Pilih Kecamatan:", district_list)
    
    if selected_district != 'Semua Kecamatan':
        df_filtered = df_filtered[df_filtered['district'] == selected_district]

    # Filter 3: Kelurahan (Dinamis berdasarkan Kecamatan)
    sub_district_list = ['Semua Kelurahan'] + sorted(list(df_filtered['sub_district'].dropna().unique()))
    selected_sub_district = st.sidebar.selectbox("Pilih Kelurahan:", sub_district_list)
    
    if selected_sub_district != 'Semua Kelurahan':
        df_filtered = df_filtered[df_filtered['sub_district'] == selected_sub_district]

    # --- Tampilan Utama ---
    st.markdown("---")

    # Metrik (Perhitungan Statistik)
    col1, col2, col3 = st.columns(3)
    total_hotspot = len(df_filtered)
    
    if total_hotspot > 0:
        top_sub_district = df_filtered['sub_district'].mode()[0]
        top_district = df_filtered['district'].mode()[0]
    else:
        top_sub_district = "N/A"
        top_district = "N/A"

    with col1:
        st.metric(label=" Total Hotspot Ditemukan", value=total_hotspot)
    with col2:
        st.metric(label=" Kecamatan Teratas (di Pilihan)", value=top_district)
    with col3:
        st.metric(label=" Kelurahan Teratas (di Pilihan)", value=top_sub_district)
    
    st.markdown("---")

    # --- Visualisasi (Tabs) ---
    tab1, tab2, tab3 = st.tabs([" Peta 3D (PyDeck)", " Analisis Data (Plotly)", " Detail Data Mentah"])

    with tab1:
        # --- BLOK PYDECK ---
        st.markdown("##  Peta 3D (PyDeck)")
        
        if not df_filtered.empty:
            try:
                # Tentukan tampilan awal peta
                view_state = pdk.ViewState(
                    latitude=df_filtered['lat'].mean(),
                    longitude=df_filtered['lon'].mean(),
                    zoom=12,  # Zoom lebih dekat
                    pitch=50  # Memberi sudut 3D
                )

                # Tentukan layer (kita gunakan 'ScatterplotLayer' untuk titik)
                layer = pdk.Layer(
                    'ScatterplotLayer',
                    data=df_filtered,
                    get_position='[lon, lat]',
                    get_color='[200, 30, 0, 160]', # Warna titik (Merah Terang)
                    get_radius=50, # Ukuran titik dalam meter
                    pickable=True # Agar bisa di-klik/hover
                )

                # Tooltip saat hover
                tooltip = {
                    'html': '<b>Nama:</b> {location_name} <br> <b>Kelurahan:</b> {sub_district}',
                    'style': {'color': 'white', 'backgroundColor': 'black'}
                }

                # Tampilkan peta Pydeck
                st.pydeck_chart(pdk.Deck(
                    map_style='mapbox://styles/mapbox/dark-v9', # Peta tema gelap dari Mapbox
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip=tooltip
                ))
                st.info(f"ℹ Menampilkan {total_hotspot} titik. Gunakan mouse untuk navigasi 3D.")
                
            except Exception as e:
                st.error(f"Error saat membuat peta PyDeck: {e}")
                st.error("Pastikan library pydeck ter-install: pip install pydeck")
        else:
            st.warning("Tidak ada data untuk ditampilkan di peta sesuai filter Anda.")
        # --- AKHIR DARI BLOK PYDECK ---

    with tab2:
        st.markdown("## Analisis Data (Plotly)")
        if not df_filtered.empty:
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.markdown("### Top 10 Kelurahan (di Area Terpilih)")
                sub_district_counts = df_filtered['sub_district'].value_counts().head(10)
                if not sub_district_counts.empty:
                    fig1 = px.bar(
                        x=sub_district_counts.values, y=sub_district_counts.index,
                        orientation='h', labels={'x': 'Jumlah Hotspot', 'y': 'Kelurahan'},
                        color=sub_district_counts.values, color_continuous_scale='Viridis',
                        template='plotly_dark'
                    )
                    fig1.update_layout(showlegend=False, height=400, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.info("Tidak ada data kelurahan untuk di-chart.")

            with chart_col2:
                st.markdown("### Distribusi per Kecamatan (di Area Terpilih)")
                district_counts = df_filtered['district'].value_counts().head(10)
                if not district_counts.empty:
                    fig2 = px.pie(
                        values=district_counts.values, names=district_counts.index,
                        title="Top 10 Kecamatan", hole=0.4,
                        template='plotly_dark'
                    )
                    fig2.update_layout(height=400)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("Tidak ada data kecamatan untuk di-chart.")
        else:
            st.warning("Tidak ada data untuk dianalisis sesuai filter Anda.")

    with tab3:
        st.markdown("## Detail Data Mentah")
        # Menampilkan kolom yang sudah di-rename
        st.dataframe(
            df_filtered[['location_name', 'region', 'district', 'sub_district', 'lat', 'lon']],
            use_container_width=True
        )
        
        # Tombol Download
        st.download_button(
            label=" Download Data Terfilter (CSV)",
            data=df_filtered.to_csv(index=False).encode('utf-8'),
            file_name='jakwifi_filtered_data.csv',
            mime='text/csv'
        )

    # Footer
    st.markdown("---")
    st.markdown("<p style='text-align: center; color: #888;'>Dibuat dengan Streamlit, PyDeck, dan Plotly</p>", unsafe_allow_html=True)

# Menjalankan fungsi utama
if __name__ == "__main__":
    main()