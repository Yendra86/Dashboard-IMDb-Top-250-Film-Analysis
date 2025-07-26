import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.pyplot as plt

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Film IMDb",
    page_icon="🎬",
    layout="wide",
)

# --- FUNGSI MEMUAT DATA ---
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)
    df['Genre_list'] = df['Genre'].str.split(', ')
    if 'User_Reviews' in df.columns and df['User_Reviews'].isnull().any():
        df['User_Reviews'] = df['User_Reviews'].fillna(0)
    if 'Bintang_Film' in df.columns:
        df['Bintang_Film'] = df['Bintang_Film'].str.split(', ')
    return df

# --- MEMUAT DATA ---
try:
    df = load_data('imdb_top_250_cleaned.csv')
except FileNotFoundError:
    st.error("File 'imdb_top_250_cleaned.csv' tidak ditemukan. Pastikan file berada di folder yang sama.")
    st.stop()

# --- SIDEBAR UNTUK FILTER ---
st.sidebar.header("🔍 Filter Pencarian")

all_genres = sorted(list(set([genre for sublist in df['Genre_list'] for genre in sublist])))
selected_genres = st.sidebar.multiselect("Pilih Genre:", options=all_genres, default=[])

min_year = int(df['Tahun'].min())
max_year = int(df['Tahun'].max())
year_range = st.sidebar.slider("Pilih Rentang Tahun Rilis:", min_value=min_year, max_value=max_year, value=(min_year, max_year))

min_rating = float(df['Rating'].min())
max_rating = float(df['Rating'].max())
rating_range = st.sidebar.slider("Pilih Rentang Rating:", min_value=min_rating, max_value=max_rating, value=(min_rating, max_rating), step=0.1)

# --- MENERAPKAN FILTER ---
filtered_df = df[
    (df['Tahun'] >= year_range[0]) & (df['Tahun'] <= year_range[1]) &
    (df['Rating'] >= rating_range[0]) & (df['Rating'] <= rating_range[1])
]
if selected_genres:
    filtered_df = filtered_df[filtered_df['Genre_list'].apply(lambda x: all(genre in x for genre in selected_genres))]

# --- TAMPILAN UTAMA DASHBOARD ---
st.title("🎬 Dashboard Analisis IMDb Top 250 Film")
st.markdown("Gunakan filter di sidebar kiri untuk menjelajahi data film sesuai keingan anda.")

# --- METRIK UTAMA ---
st.markdown("### 📈 Metrik Utama")
col1, col2, col3 = st.columns(3)
avg_rating = f"⭐ {filtered_df['Rating'].mean():.2f}" if not filtered_df.empty else "N/A"
avg_duration = f"🕰️ {filtered_df['Durasi_Menit'].mean():.0f} Menit" if not filtered_df.empty else "N/A"
col1.metric("Total Film Ditemukan", f"🎞️ {filtered_df.shape[0]}")
col2.metric("Rating Rata-rata", avg_rating)
col3.metric("Durasi Rata-rata", avg_duration)

st.markdown("---")
st.markdown(f"### 🎞️ Menampilkan {filtered_df.shape[0]} Film")
if filtered_df.empty:
    st.warning("Tidak ada film yang cocok dengan kriteria filter Anda.")
else:
    st.dataframe(
        filtered_df[['Peringkat', 'Judul', 'Tahun', 'Rating', 'Sutradara', 'Genre']],
        hide_index=True, use_container_width=True,
        column_config={
            "Rating": st.column_config.ProgressColumn("Rating", format="%.1f", min_value=df['Rating'].min(), max_value=df['Rating'].max()),
            "Tahun": st.column_config.NumberColumn(format="%d"),
        }
    )

# --- VISUALISASI ---
if not filtered_df.empty:
    st.markdown("### 📊 Visualisasi Data")

    # Jumlah Film per Dekade
    st.subheader("📆 Jumlah Film per Dekade")
    df_vis = filtered_df.copy()
    df_vis['Dekade'] = (df_vis['Tahun'] // 10) * 10
    movies_per_decade = df_vis['Dekade'].value_counts().sort_index()
    st.bar_chart(movies_per_decade)

    # Top Sutradara
    st.subheader("🎬 Top 10 Sutradara dengan Film Terbanyak")
    top_directors = filtered_df['Sutradara'].value_counts().nlargest(10)
    st.bar_chart(top_directors)

    # Rata-rata Rating per Genre
    st.subheader("🎭 Rata-rata Rating per Genre")
    genre_exploded = filtered_df.explode('Genre_list')
    genre_rating = genre_exploded.groupby('Genre_list')['Rating'].mean().reset_index().sort_values('Rating', ascending=False)
    bar = alt.Chart(genre_rating).mark_bar().encode(
        x=alt.X('Rating:Q', title='Rating Rata-rata'),
        y=alt.Y('Genre_list:N', sort='-x', title='Genre'),
        tooltip=['Genre_list', 'Rating']
    ).properties(width=700, height=400)
    st.altair_chart(bar, use_container_width=True)

    # Aktor/Aktris paling sering muncul
    if 'Bintang_Film' in filtered_df.columns:
        st.subheader("🌟 Top 10 Aktor/Aktris Paling Sering Muncul")
        stars_exploded = filtered_df.explode('Bintang_Film')
        top_stars = stars_exploded['Bintang_Film'].value_counts().nlargest(10)
        st.bar_chart(top_stars)

    # Heatmap Genre vs Dekade
    st.subheader("🔥 Heatmap Rating Rata-rata per Genre & Dekade")
    genre_decade = genre_exploded.copy()
    genre_decade['Dekade'] = (genre_decade['Tahun'] // 10) * 10
    pivot_table = genre_decade.pivot_table(index='Genre_list', columns='Dekade', values='Rating', aggfunc='mean')
    st.dataframe(pivot_table.style.background_gradient(cmap='YlGnBu'), use_container_width=True)

    # Treemap Genre
    st.subheader("🌳 Treemap Genre berdasarkan Jumlah dan Rating")

    genre_stats = genre_exploded.groupby('Genre_list').agg({'Rating': ['count', 'mean']})
    genre_stats.columns = ['Jumlah_Film', 'Rata_Rata_Rating']
    genre_stats = genre_stats.reset_index()

    fig = px.treemap(
        genre_stats,
        path=['Genre_list'],
        values='Jumlah_Film',
        color='Rata_Rata_Rating',
        color_continuous_scale='RdBu',
        title='Distribusi Genre Berdasarkan Jumlah Film dan Rating'
    )
    st.plotly_chart(fig, use_container_width=True)


    # Scatter Plot Durasi vs Rating
    st.subheader("📌 Hubungan Durasi dan Rating Film (Scatter Plot)")

    filtered_df['Main_Genre'] = filtered_df['Genre_list'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "Unknown")
    fig = px.scatter(
        filtered_df,
        x="Durasi_Menit",
        y="Rating",
        color="Main_Genre",
        hover_data=["Judul", "Tahun", "Sutradara"],
        title="Durasi vs Rating Film",
        labels={"Durasi_Menit": "Durasi (menit)", "Rating": "Rating IMDb"}
    )
    st.plotly_chart(fig, use_container_width=True)

    # Word Cloud Sutradara
    st.subheader("☁️ Word Cloud Sutradara")
    directors_text = ' '.join(filtered_df['Sutradara'].dropna().tolist())
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(directors_text)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig)

# --- OPSIONAL: TAMPILKAN RAW DATA ---
if st.sidebar.checkbox("Tampilkan data mentah"):
    st.markdown("---")
    st.subheader("📄 Data Mentah (Raw Data)")
    st.write(df)
