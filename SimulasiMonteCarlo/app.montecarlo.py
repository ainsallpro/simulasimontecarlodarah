import pandas as pd
import os
import random
import math
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

# --- Konfigurasi Aplikasi ---
FILE_PATHS = {
    'A': "Prob A.xlsx",
    'B': "Prob B.xlsx",
    'AB': "Prob AB.xlsx",
    'O': "Prob O.xlsx"
}

# Pengaturan Warna Untuk Grafik
PLOT_COLORS = {
    'A': '#1f77b4', # Biru gelap
    'B': '#ff7f0e', # Oranye
    'AB': '#d62728', # Merah
    'O': '#2ca02c', # Hijau
}

# Jumlah simulasi yang akan dijalankan (tidak ada nilai default di sini agar input kosong)
# NUM_SIMULATIONS_DEFAULT = 84 # Dihapus atau dikomentari karena kita ingin input kosong secara default

# --- Fungsi Pembantu (Helper Functions) ---

def clean_interval_string(interval_str):
    """
    Membersihkan dan menstandarkan format string interval (misal: '103â-130' menjadi '103-130').
    """
    return str(interval_str).replace('â', '-').replace('–', '-').replace('—', '-').replace(' ', '').replace(',', '')

def parse_interval(interval_str):
    """
    Mengurai string interval 'a-b' dan mengembalikan tuple (a, b) dalam bentuk integer.
    Mengembalikan (None, None) jika terjadi error parsing.
    """
    try:
        a, b = map(int, interval_str.split('-'))
        return a, b
    except ValueError:
        return None, None

# --- Fungsi Pemuatan dan Pra-pemrosesan Data ---

@st.cache_data # Menggunakan cache Streamlit untuk mempercepat pemuatan data Excel
def load_distribusi_from_excel(file_path):
    """
    Memuat data distribusi golongan darah dari file Excel.
    Memastikan kolom yang dibutuhkan ada dan mengonversi tipe data yang sesuai.

    Args:
        file_path (str): Path lengkap ke file Excel.

    Returns:
        pd.DataFrame: DataFrame berisi data distribusi yang sudah diproses,
                      atau DataFrame kosong jika terjadi error.
    """
    try:
        df = pd.read_excel(file_path)
        # Memfilter baris yang memiliki nilai kosong di 'Interval Kelas ' atau 'Probabilitas'
        df = df[df['Interval Kelas '].notna() & df['Probabilitas'].notna()].copy()

        # Mengonversi kolom yang relevan ke float, menangani koma sebagai pemisah desimal
        df['Probabilitas'] = df['Probabilitas'].astype(str).str.replace(',', '.').astype(float)
        df['Prob Kumulatif '] = df['Prob Kumulatif '].astype(str).str.replace(',', '.').astype(float) # Pastikan spasi di akhir nama kolom
        df['Prob Kumulatif * 100'] = df['Prob Kumulatif * 100'].astype(str).str.replace(',', '.').astype(float)

        return df[['No', 'Interval Kelas ', 'Frekuensi', 'Probabilitas', 'Prob Kumulatif ', 'Prob Kumulatif * 100']].reset_index(drop=True)
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat {file_path}: {e}")
        return pd.DataFrame()

@st.cache_data # Menggunakan cache Streamlit untuk mempercepat pemuatan semua distribusi
def load_all_distributions(file_paths):
    """
    Memuat data distribusi untuk semua golongan darah yang ditentukan.

    Args:
        file_paths (dict): Dictionary yang memetakan golongan darah ke path filenya.

    Returns:
        dict: Dictionary di mana kunci adalah golongan darah dan nilai adalah DataFrame
              yang berisi data distribusi mereka.
    """
    distribusi_dict = {}
    for gol, path in file_paths.items():
        if os.path.exists(path):
            distribusi_dict[gol] = load_distribusi_from_excel(path)
        else:
            st.warning(f"File untuk golongan darah {gol} tidak ditemukan di: {path}")
    return distribusi_dict

# --- Fungsi Tampilan Data ---

def display_distribution_table(df, golongan):
    """
    Menampilkan tabel distribusi yang diformat untuk golongan darah tertentu di Streamlit.
    Termasuk kolom 'Titik Tengah' dan menyembunyikan indeks default Pandas.

    Args:
        df (pd.DataFrame): DataFrame yang berisi data distribusi.
        golongan (str): Golongan darah (misal: 'A', 'B', 'AB', 'O').
    """
    st.subheader(f"Tabel Distribusi Golongan Darah {golongan} 📋")
    
    display_df = df.copy()
    
    # 1. Hitung dan tambahkan kolom 'Titik Tengah'
    midpoints = []
    for _, row in display_df.iterrows():
        interval = clean_interval_string(row['Interval Kelas '])
        a, b = parse_interval(interval)
        if a is not None and b is not None:
            midpoints.append(math.ceil((a + b) / 2)) # Pembulatan ke atas
        else:
            midpoints.append(None) # Jika parsing interval gagal
    display_df['Titik Tengah'] = midpoints # Tambahkan kolom baru

    # 2. Siapkan kolom 'Interval Angka Acak'
    display_df['Interval Angka Acak'] = ""
    lower_bound = 0
    for i, row in display_df.iterrows():
        upper_bound = int(round(row['Prob Kumulatif * 100']))
        display_df.loc[i, 'Interval Angka Acak'] = f"{str(lower_bound).zfill(2)} - {str(upper_bound).zfill(2)}"
        lower_bound = upper_bound + 1
    
    # 3. Bersihkan string interval dan ganti nama kolom untuk tampilan yang lebih baik
    display_df['Interval Kelas '] = display_df['Interval Kelas '].apply(clean_interval_string)
    display_df = display_df.rename(columns={
        'Interval Kelas ': 'Interval Kelas',
        'Prob Kumulatif ': 'Prob Kumulatif' # Memastikan konsistensi nama kolom
    })
    
    # 4. Tentukan urutan kolom yang akan ditampilkan
    cols_to_display = [
        'No',
        'Interval Kelas',
        'Frekuensi',
        'Probabilitas',
        'Prob Kumulatif',
        'Prob Kumulatif * 100',
        'Titik Tengah',  # Kolom baru "Titik Tengah"
        'Interval Angka Acak'
    ]
    
    # 5. Tampilkan DataFrame di Streamlit dan sembunyikan indeks default Pandas
    st.dataframe(display_df[cols_to_display], hide_index=True)

# --- Logika Simulasi ---

def get_simulation_value(df, random_number):
    """
    Menentukan nilai simulasi berdasarkan angka acak dan distribusi yang diberikan.

    Args:
        df (pd.DataFrame): DataFrame distribusi untuk golongan darah tertentu.
        random_number (int): Angka acak yang dihasilkan (0-99).

    Returns:
        int: Titik tengah dari interval yang sesuai dengan angka acak,
             atau 0 jika tidak ditemukan atau terjadi error.
    """
    lower_bound = 0
    for _, row in df.iterrows():
        upper_bound = int(round(row['Prob Kumulatif * 100']))
        if lower_bound <= random_number <= upper_bound:
            interval = clean_interval_string(row['Interval Kelas '])
            a, b = parse_interval(interval)
            if a is not None and b is not None:
                return math.ceil((a + b) / 2)
            else:
                return 0
        lower_bound = upper_bound + 1
    return 0

@st.cache_data # Menggunakan cache untuk hasil simulasi agar lebih cepat jika inputnya sama
def run_monte_carlo_simulation(distribusi_dict, num_simulations):
    """
    Menjalankan simulasi Monte Carlo untuk pemakaian darah.

    Args:
        distribusi_dict (dict): Dictionary dari DataFrame distribusi golongan darah.
        num_simulations (int): Jumlah periode simulasi yang akan dijalankan.

    Returns:
        pd.DataFrame: DataFrame yang berisi hasil dari setiap periode simulasi.
    """
    simulation_results = []
    
    # Untuk menampilkan progress di Streamlit
    progress_text = "Simulasi sedang berjalan. Mohon tunggu. ⏳"
    my_bar = st.progress(0, text=progress_text)

    for i in range(num_simulations):
        a_acak = random.randint(0, 99)
        b_acak = random.randint(0, 99)
        ab_acak = random.randint(0, 99)
        o_acak = random.randint(0, 99)

        sim_a = get_simulation_value(distribusi_dict.get('A', pd.DataFrame()), a_acak)
        sim_b = get_simulation_value(distribusi_dict.get('B', pd.DataFrame()), b_acak)
        sim_ab = get_simulation_value(distribusi_dict.get('AB', pd.DataFrame()), ab_acak)
        sim_o = get_simulation_value(distribusi_dict.get('O', pd.DataFrame()), o_acak)

        total_sim = sim_a + sim_b + sim_ab + sim_o

        # Menghitung persentase, menangani pembagian nol
        pa = (sim_a / total_sim * 100) if total_sim else 0
        pb = (sim_b / total_sim * 100) if total_sim else 0
        pab = (sim_ab / total_sim * 100) if total_sim else 0
        po = (sim_o / total_sim * 100) if total_sim else 0

        simulation_results.append({
            'Periode': i + 1, 
            'Angka Acak A': a_acak,
            'Angka Acak B': b_acak,
            'Angka Acak AB': ab_acak,
            'Angka Acak O': o_acak,
            'Simulasi A': sim_a,
            'Simulasi B': sim_b,
            'Simulasi AB': sim_ab,
            'Simulasi O': sim_o,
            'Total Simulasi': total_sim,
            'Pmk A%': pa,
            'Pmk B%': pb,
            'Pmk AB%': pab,
            'Pmk O%': po
        })
        # Update progress bar
        my_bar.progress((i + 1) / num_simulations, text=progress_text)
        
    my_bar.empty() # Hapus progress bar setelah selesai
    return pd.DataFrame(simulation_results)

# --- Analisis dan Visualisasi ---

def perform_summary_analysis(sim_df):
    """
    Melakukan dan menampilkan statistik ringkasan serta wawasan penting dari simulasi.

    Args:
        sim_df (pd.DataFrame): DataFrame yang berisi hasil simulasi.
    """
    # Menghitung statistik ringkasan untuk pemakaian darah
    summary_stats = sim_df[['Simulasi A', 'Simulasi B', 'Simulasi AB', 'Simulasi O', 'Total Simulasi']].agg(['mean', 'std', 'min', 'max']).transpose()
    summary_stats.columns = ['Rata-rata', 'Standar Deviasi', 'Minimum', 'Maksimum']
    st.markdown("### Statistik Ringkasan Pemakaian Darah (kantong) 📊:")
    st.dataframe(summary_stats.round(2))

    # Mengidentifikasi periode dengan total pemakaian tinggi/rendah
    if not sim_df.empty:
        max_total_usage_period = sim_df.loc[sim_df['Total Simulasi'].idxmax()]
        min_total_usage_period = sim_df.loc[sim_df['Total Simulasi'].idxmin()]

        st.markdown(f"### Periode dengan Total Pemakaian Tertinggi 📈:")
        st.markdown(f"   Periode **{int(max_total_usage_period['Periode'])}** (Total: **{int(max_total_usage_period['Total Simulasi'])}** kantong)")
        st.markdown(f"   - Komposisi: A={int(max_total_usage_period['Simulasi A'])}, B={int(max_total_usage_period['Simulasi B'])}, AB={int(max_total_usage_period['Simulasi AB'])}, O={int(max_total_usage_period['Simulasi O'])}")

        st.markdown(f"### Periode dengan Total Pemakaian Terendah 📉:")
        st.markdown(f"   Periode **{int(min_total_usage_period['Periode'])}** (Total: **{int(min_total_usage_period['Total Simulasi'])}** kantong)")
        st.markdown(f"   - Komposisi: A={int(min_total_usage_period['Simulasi A'])}, B={int(min_total_usage_period['Simulasi B'])}, AB={int(min_total_usage_period['Simulasi AB'])}, O={int(min_total_usage_period['Simulasi O'])}")
    else:
        st.info("Tidak ada data simulasi untuk ringkasan analisis.")

def provide_decision_insights(sim_df):
    """
    Memberikan wawasan dan rekomendasi untuk pengambil keputusan berdasarkan hasil simulasi.
    """
    st.markdown("---")
    st.header("💡 WAWASAN & REKOMENDASI UNTUK PENGAMBIL KEPUTUSAN 🎯")
    st.markdown("---")

    if sim_df.empty:
        st.info("Tidak ada data simulasi untuk memberikan wawasan atau rekomendasi.")
        return

    # Hitung rata-rata pemakaian untuk setiap golongan darah
    avg_pemakaian_a = sim_df['Simulasi A'].mean()
    avg_pemakaian_b = sim_df['Simulasi B'].mean()
    avg_pemakaian_ab = sim_df['Simulasi AB'].mean()
    avg_pemakaian_o = sim_df['Simulasi O'].mean()
    
    total_avg_usage = sim_df['Total Simulasi'].mean()
    
    # Urutkan golongan darah berdasarkan rata-rata pemakaian (dari tertinggi ke terendah)
    avg_usages = {
        'A': avg_pemakaian_a,
        'B': avg_pemakaian_b,
        'AB': avg_pemakaian_ab,
        'O': avg_pemakaian_o
    }
    sorted_avg_usages = sorted(avg_usages.items(), key=lambda item: item[1], reverse=True)

    st.markdown(f"Dari hasil simulasi **{len(sim_df)} periode**, kita bisa melihat beberapa hal penting terkait pemakaian darah:\n")

    st.markdown(f"**1. Prediksi Kebutuhan Darah Secara Umum: 🩸**")
    st.markdown(f"   Rata-rata total pemakaian darah per periode adalah sekitar **{total_avg_usage:.0f} kantong**.\n")

    st.markdown(f"**2. Golongan Darah Paling Banyak dan Paling Sedikit Digunakan: 📊**")
    st.markdown(f"   Berdasarkan rata-rata pemakaian:\n")
    for blood_type, avg_usage in sorted_avg_usages:
        st.markdown(f"   - **Golongan {blood_type}:** Rata-rata pemakaian sekitar **{avg_usage:.0f} kantong per periode**.")
    
    st.markdown(f"\n   Dari sini, kita bisa tahu golongan darah mana yang punya permintaan paling tinggi yaitu **Golongan {sorted_avg_usages[0][0]}** dan paling rendah yaitu **Golongan {sorted_avg_usages[-1][0]}**.\n")

    st.markdown(f"**3. Strategi Pengelolaan Stok: 📦**")
    st.markdown(f"   - **Untuk golongan darah dengan pemakaian tinggi Golongan {sorted_avg_usages[0][0]} dan {sorted_avg_usages[1][0]}:** Pastikan stoknya selalu mencukupi.")
    st.markdown(f"   - **Untuk golongan darah dengan pemakaian rendah Golongan {sorted_avg_usages[-1][0]}:** Tetap harus ada stok, tapi mungkin bisa dikelola agar tidak terlalu banyak menumpuk.")

    if not sim_df.empty:
        max_total_usage_period = sim_df.loc[sim_df['Total Simulasi'].idxmax()]
        min_total_usage_period = sim_df.loc[sim_df['Total Simulasi'].idxmin()]
        
        st.markdown(f"**4. Antisipasi Periode Puncak dan Rendah: 🗓️**")
        st.markdown(f"   - Periode dengan pemakaian tertinggi terjadi di **periode {int(max_total_usage_period['Periode'])}** dengan total **{int(max_total_usage_period['Total Simulasi'])}** kantong.")
        st.markdown(f"   - Periode dengan pemakaian terendah terjadi di **periode {int(min_total_usage_period['Periode'])}** dengan total **{int(min_total_usage_period['Total Simulasi'])}** kantong.\n")

def plot_blood_usage_bar_chart(sim_df, colors):
    """
    Menggambar grafik batang yang menunjukkan pemakaian darah simulasi per golongan darah per periode.
    Ukuran grafik disesuaikan agar lebih besar dan jelas.

    Args:
        sim_df (pd.DataFrame): DataFrame yang berisi hasil simulasi.
        colors (dict): Dictionary yang memetakan golongan darah ke warna grafiknya.
    """
    # Meningkatkan ukuran figur untuk tampilan yang lebih besar dan jelas
    fig, ax = plt.subplots(figsize=(50, 25))

    bar_width = 0.2
    r1 = np.arange(len(sim_df))
    r2 = [x + bar_width for x in r1]
    r3 = [x + bar_width * 2 for x in r1]
    r4 = [x + bar_width * 3 for x in r1]

    # Menggambar setiap golongan darah sebagai batang
    ax.bar(r1, sim_df['Simulasi A'], color=colors['A'], width=bar_width, edgecolor='black', label='Simulasi A', alpha=0.9)
    ax.bar(r2, sim_df['Simulasi B'], color=colors['B'], width=bar_width, edgecolor='black', label='Simulasi B', alpha=0.9)
    ax.bar(r3, sim_df['Simulasi AB'], color=colors['AB'], width=bar_width, edgecolor='black', label='Simulasi AB', alpha=0.9)
    ax.bar(r4, sim_df['Simulasi O'], color=colors['O'], width=bar_width, edgecolor='black', label='Simulasi O', alpha=0.9)

    # Judul dan label sumbu
    ax.set_xlabel('Periode Simulasi', fontweight='bold', fontsize=14, labelpad=10)
    ax.set_ylabel('Jumlah Pemakaian Darah (kantong)', fontweight='bold', fontsize=14, labelpad=10)
    ax.set_title('GRAFIK SIMULASI PEMAKAIAN DARAH PER PERIODE', fontweight='bold', fontsize=20, pad=20)

    # Label sumbu X (periode simulasi)
    if not sim_df.empty:
        ax.set_xticks(
            [r + bar_width * 1.5 for r in range(len(sim_df))],
            labels=sim_df['Periode'],
            rotation=90,
            ha='center',
            fontsize=8
        )
    else:
        st.info("DataFrame simulasi kosong, tidak dapat menampilkan label sumbu X.")

    # Batas sumbu Y dan tick Y
    max_y_value = sim_df['Total Simulasi'].max() if not sim_df.empty else 0
    ax.set_yticks(np.arange(0, max_y_value + 200, 200))
    ax.tick_params(axis='y', labelsize=12)

    ax.set_ylim(0, max_y_value + 200)

    # Grid dan legend di bawah grafik
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.legend(
        fontsize=12,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.15),
        ncol=4
    )

    # Mengatur layout agar tidak terpotong
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    fig.subplots_adjust(bottom=0.2, top=0.9)

    st.pyplot(fig)

def plot_average_usage_pie_chart(sim_df, colors):
    """
    Menggambar grafik pai yang menunjukkan rata-rata pemakaian darah simulasi per golongan darah.

    Args:
        sim_df (pd.DataFrame): DataFrame yang berisi hasil simulasi.
        colors (dict): Dictionary yang memetakan golongan darah ke warna grafiknya.
    """
    # Menghitung rata-rata pemakaian untuk setiap golongan darah
    avg_pemakaian_a = sim_df['Simulasi A'].mean()
    avg_pemakaian_b = sim_df['Simulasi B'].mean()
    avg_pemakaian_ab = sim_df['Simulasi AB'].mean()
    avg_pemakaian_o = sim_df['Simulasi O'].mean()

    # Data untuk grafik pai
    labels = ['PEMAKAIAN A', 'PEMAKAIAN B', 'PEMAKAIAN AB', 'PEMAKAIAN O']
    sizes = [avg_pemakaian_a, avg_pemakaian_b, avg_pemakaian_ab, avg_pemakaian_o]
    
    # Warna yang konsisten dengan PLOT_COLORS
    pie_colors = [colors['A'], colors['B'], colors['AB'], colors['O']] 

    # Membuat grafik pai
    # Mengurangi ukuran figur menjadi (4, 3) agar lebih kecil
    fig, ax = plt.subplots(figsize=(3, 2)) 
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=pie_colors,
            wedgeprops={'edgecolor': 'black'},
            textprops={'fontsize': 8})
    ax.set_title('RATA-RATA PEMAKAIAN SIMULASI DARAH PER GOLONGAN', fontweight='bold', fontsize=10, pad=10)
    ax.axis('equal') 
    
    st.pyplot(fig)


# --- Eksekusi Program Utama (Main Execution) ---

if __name__ == "__main__":
    # Mengatur konfigurasi halaman Streamlit
    st.set_page_config(layout="wide", page_title="Simulasi Monte Carlo Pemakaian Darah")
    
    # Menambahkan custom CSS untuk background dan centering title
    st.markdown(
        """
        <style>
        .main {
            background-color: #f0f2f6; /* Warna latar belakang yang lembut */
            background-image: linear-gradient(to bottom right, #f0f2f6, #e0e4eb); /* Gradien lembut */
            color: #333333; /* Warna teks umum */
        }
        .stButton>button {
            background-color: #4CAF50; /* Warna hijau untuk tombol */
            color: white;
            border-radius: 12px;
            padding: 10px 24px;
            border: none;
            cursor: pointer;
            font-size: 16px;
            box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #45a049;
            box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
        }
        h1 {
            text-align: center;
            color: #1a1a1a; /* Warna judul yang lebih gelap */
        }
        h2, h3 {
            color: #2c3e50; /* Warna sub-judul */
        }
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem; /* Ukuran font tab */
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h1 style='text-align: center;'>🩸 Simulasi Pemakaian Darah di UTD RSUD dr. Soekardjo Kota Tasikmalaya pada 2021-2023 dengan Simulasi Monte Carlo 🩸</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # 1. Pemuatan Data Distribusi
    st.header("1. 📊 Data Distribusi Golongan Darah")
    distribusi_data = load_all_distributions(FILE_PATHS)

    # Menampilkan Tabel Distribusi dalam bentuk tab untuk kerapian
    tab_titles = list(FILE_PATHS.keys())
    tabs = st.tabs(tab_titles)

    for i, gol in enumerate(FILE_PATHS.keys()):
        with tabs[i]:
            if gol in distribusi_data and not distribusi_data[gol].empty:
                display_distribution_table(distribusi_data[gol], gol)
            else:
                st.warning(f"Data distribusi untuk Golongan Darah {gol} tidak tersedia. ⚠️")

    # 2. Menjalankan Simulasi Monte Carlo
    st.markdown("---")
    st.header("2. 🧪 Hasil Simulasi Monte Carlo")
    
    # Input teks untuk jumlah periode simulasi, sekarang kosong secara default
    num_simulations_str = st.text_input(
        "Pilih Jumlah Periode Simulasi:",
        value="",  # Ini yang diubah menjadi string kosong
        help="Masukkan jumlah periode simulasi (misal: 84, 120, 365).",
        key="num_sim_input"
    )
    
    # Tombol untuk menjalankan simulasi
    if st.button('Jalankan Simulasi ▶️'):
        num_simulations_input = 0 # Inisialisasi
        is_valid_input = True

        try:
            num_simulations_input = int(num_simulations_str)
            if num_simulations_input <= 0:
                st.error("Jumlah periode simulasi harus lebih besar dari 0. ❌")
                is_valid_input = False
        except ValueError:
            st.error("Input tidak valid. Harap masukkan angka bulat untuk jumlah periode simulasi. 🔢")
            is_valid_input = False

        if is_valid_input:
            # Menampilkan indikator loading saat simulasi berjalan
            with st.spinner(f'Menjalankan simulasi untuk {num_simulations_input} periode... Ini mungkin butuh waktu. ⏳'):
                simulation_df = run_monte_carlo_simulation(distribusi_data, num_simulations_input)
            
            # 3. Menampilkan Hasil Simulasi
            st.subheader("Tabel Hasil Simulasi Per Periode: 📊")
            if not simulation_df.empty:
                st.dataframe(simulation_df.round(2), hide_index=True)
            else:
                st.warning("Tidak ada hasil simulasi yang dihasilkan. ⚠️")

            # 4. Melakukan Analisis dan Menghasilkan Visualisasi
            if not simulation_df.empty:
                st.markdown("---")
                st.header("3. 📈 Analisis dan Visualisasi")

                # --- Penempatan Visualisasi (Grafik) ---
                st.subheader("Visualisasi Data Simulasi: 📉📈")
                plot_blood_usage_bar_chart(simulation_df, PLOT_COLORS)
                plot_average_usage_pie_chart(simulation_df, PLOT_COLORS)
                # --- Akhir Penempatan Visualisasi ---
            
                # Analisis Teks (Statistik Ringkasan & Wawasan) setelah grafik
                perform_summary_analysis(simulation_df)
                provide_decision_insights(simulation_df) 

            else:
                st.error("Tidak ada hasil simulasi untuk dianalisis atau ditampilkan. Pastikan data distribusi tersedia dan simulasi berjalan dengan benar. ⚠️")
        else:
            st.info("Masukkan jumlah periode simulasi yang valid untuk memulai analisis.")
    else:
        st.info("Tekan tombol 'Jalankan Simulasi ▶️' di atas untuk memulai analisis.")