import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os

# Configuration initiale
st.set_page_config(page_title="Analyse avancée", layout="wide")
st.markdown('<h1 style="color:yellow;">📊 Analyse des Restaurants</h1>', unsafe_allow_html=True)

# Connexion
load_dotenv()
token = os.getenv("mother_duck_token")
db_path = f"md:my_db?motherduck_token={token}"
con = duckdb.connect(db_path)

# Chargement des données
query = """
SELECT ville, "spécialité", "niveau de prix (libellé)", latitude, longitude, nom, notation
FROM restaurants_france_cleaned
"""
data = con.execute(query).fetchdf()

# Afficher nombre total de restaurants
total_restaurants = len(data)
st.info(f"🗂️ Nombre total de restaurants pour l'étude : **{total_restaurants}**")
with st.expander("🔎 Méthodologie utilisée (collecte, traitement et visualisation)"):
    st.markdown("""
    <style>
        ul {
            list-style-type: disc;
            margin-left: 20px;
        }
        ul ul {
            list-style-type: circle;
        }
        h4 {
            margin-top: 1.5em;
            color: #FFA500;
        }
    </style>

    <h4>1. Collecte des données :</h4>
    <ul>
        <li>Utilisation de l’API <strong>Google Places</strong> pour récupérer des informations sur les restaurants dans plusieurs grandes villes françaises.</li>
        <li>Données extraites : nom, adresse, spécialité (type de cuisine), niveau de prix, notation, latitude/longitude, etc.</li>
    </ul>

    <h4>2. Nettoyage et traitement :</h4>
    <ul>
        <li>Suppression des doublons et des entrées incomplètes (valeurs manquantes).</li>
        <li>Harmonisation des noms de villes et des spécialités.</li>
        <li>Conversion des notations en format numérique pour permettre les analyses statistiques.</li>
        <li>Enrichissement des données avec des colonnes dérivées (ville, prix, catégorie...).</li>
    </ul>

    <h4>3. Stockage dans MotherDuck (via DuckDB) :</h4>
    <ul>
        <li>Sauvegarde locale des données au format <code>.csv</code>.</li>
        <li>Intégration dans une base de données <strong>DuckDB</strong> connectée à <strong>MotherDuck</strong>, facilitant les requêtes SQL performantes directement depuis Python.</li>
    </ul>

    <h4>4. Visualisation des données avec Streamlit :</h4>
    <ul>
        <li>Application développée dans <strong>Visual Studio Code</strong>.</li>
        <li>Interface interactive construite avec <strong>Streamlit</strong> et <strong>Plotly Express</strong>.</li>
        <li>Visualisations proposées :
            <ul>
                <li>Répartition des spécialités les plus fréquentes</li>
                <li>Nombre de restaurants par ville et spécialité</li>
                <li>Analyse des niveaux de prix</li>
                <li>Notes moyennes par ville et spécialité</li>
                <li>Classements globaux selon divers critères</li>
            </ul>
        </li>
    </ul>

    <div style="margin: 10px 0; padding: 15px; background-color: #FFA500; color: black; border-left: 6px solid #cc7000; font-size: 16px; border-radius: 6px;">
        👉 Ces visualisations visent à fournir une compréhension claire des dynamiques gastronomiques dans les grandes villes françaises, à partir d'une base de données fiable et visualisée de manière intuitive.
    </div>

    <h4>5. 🤖 Interaction via chatbot intelligent :</h4>
    <ul>
        <li>Intégration d’un <strong>chatbot interactif</strong> directement dans l’application Streamlit.</li>
        <li>Permet de poser des questions en langage naturel (ex : <em>Quel est le type de cuisine le plus courant à Lyon ?</em>).</li>
        <li>Le chatbot interroge automatiquement la base de données pour fournir des réponses précises en temps réel.</li>
    </ul>

    <hr />
    🔗 <a href="https://github.com/ton-projet" target="_blank">Voir le projet sur VS Code</a><br>
    🌐 <a href="https://nom-app.streamlit.app" target="_blank">Accéder à l'application Streamlit</a>
    """, unsafe_allow_html=True)

# Liste des villes sélectionnées
villes_selectionnees = [
    "Paris", "Lyon", "Marseille", "Avignon", "Bordeaux",
    "La Rochelle", "Toulouse", "Toulon", "Aix en Provence",
    "Brest", "Strasbourg"
]

data_clean = data.dropna(subset=['spécialité', 'ville'])

# Filtrer pour les villes sélectionnées
data_villes = data_clean[data_clean['ville'].isin(villes_selectionnees)]

# Nombre de restaurants par spécialité et ville
counts = data_villes.groupby(['ville', 'spécialité']).size().reset_index(name='nombre')

# Top 5 spécialités globales
spec_totals = counts.groupby('spécialité')['nombre'].sum().reset_index().sort_values(by='nombre', ascending=False)
top_specs = spec_totals.head(5)['spécialité'].tolist()

# 📍 Carte interactive des meilleurs restaurants (notation >= 4.5)
st.subheader("🌍 Carte des meilleurs restaurants (notation ≥ 4.5)")

# Filtrage des meilleurs restaurants
restos_top_notes = data[
    (data['notation'] >= 4.5) &
    (data['latitude'].notna()) &
    (data['longitude'].notna())
]

if not restos_top_notes.empty:
    map_fig = px.scatter_mapbox(
        restos_top_notes,
        lat="latitude",
        lon="longitude",
        color="notation",
        size_max=10,
        zoom=5,
        hover_name="nom",
        hover_data={
            "ville": True,
            "spécialité": True,
            "notation": ':.2f',
            "latitude": False,
            "longitude": False
        },
        color_continuous_scale="YlOrRd",
        title="📍 Localisation des restaurants avec note ≥ 4.5"
    )
    map_fig.update_layout(mapbox_style="open-street-map", height=600)
    map_fig.update_layout(margin={"r":0,"t":50,"l":0,"b":0})
    st.plotly_chart(map_fig, use_container_width=True)
else:
    st.warning("Aucun restaurant avec une note supérieure ou égale à 4.5 n'a été trouvé.")

# 3. Top spécialité par ville (note moyenne la plus élevée)
st.subheader("🏆 Spécialité la mieux notée par ville (parmi les 3 principales)")

# Filtrage
data['notation'] = pd.to_numeric(data['notation'], errors='coerce')
filtered_data = data[
    (data['spécialité'].isin(top_specs)) &
    (data['ville'].isin(villes_selectionnees))
].dropna(subset=['notation'])

# Calcul note moyenne par ville/spécialité
grouped = (
    filtered_data
    .groupby(['ville', 'spécialité'])['notation']
    .mean()
    .reset_index()
)

# Récupérer la spécialité avec la meilleure note moyenne par ville
idx = grouped.groupby('ville')['notation'].idxmax()
best_specialities = grouped.loc[idx].sort_values(by='notation', ascending=False)

# Affichage
fig_best_spec = px.bar(
    best_specialities,
    x='ville',
    y='notation',
    color='spécialité',
    title="🏅 Meilleure spécialité par ville (en fonction de la note moyenne)",
    labels={'notation': 'Note moyenne', 'ville': 'Ville', 'spécialité': 'Spécialité'},
    text=best_specialities['notation'].apply(lambda x: f"{x:.2f}")
)
fig_best_spec.update_traces(textposition='outside')
fig_best_spec.update_layout(barmode='group')
st.plotly_chart(fig_best_spec, use_container_width=True)

# 3. Heatmap note moyenne par ville et spécialité
st.subheader("🔶 Carte thermique : Note moyenne par spécialité et par ville (top 5 spécialités)")

# Nettoyage
data['notation'] = pd.to_numeric(data['notation'], errors='coerce')
filtered_data = data[
    (data['spécialité'].isin(top_specs)) &
    (data['ville'].isin(villes_selectionnees))
].dropna(subset=['notation'])

# Moyenne des notes
mean_notes = (
    filtered_data
    .groupby(['ville', 'spécialité'])['notation']
    .mean()
    .reset_index()
)

# Pivot pour heatmap
heatmap_df = mean_notes.pivot(index="ville", columns="spécialité", values="notation").round(2)

# Affichage avec plotly
fig_heatmap = px.imshow(
    heatmap_df,
    text_auto=True,
    color_continuous_scale='YlOrRd',
    labels=dict(x="Spécialité", y="Ville", color="Note moyenne"),
    aspect="auto",
    title="💡 Heatmap des notes moyennes par spécialité et par ville"
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# 4. Bar chart restaurants Bon marché (top 10 villes)
st.subheader("💰 Top 10 villes avec restaurants Bon marché")
query_bon_marche = '''
SELECT ville, COUNT(*) AS nombre_restaurants
FROM restaurants_france_cleaned
WHERE "niveau de prix (libellé)" = 'Bon marché'
GROUP BY ville
ORDER BY nombre_restaurants DESC
LIMIT 10
'''
bon_marche_df = con.execute(query_bon_marche).fetchdf()
if not bon_marche_df.empty:
    fig_bon_marche = px.bar(
        bon_marche_df,
        x='ville',
        y='nombre_restaurants',
        color_discrete_sequence=['orange'],
        labels={'ville': 'Ville', 'nombre_restaurants': 'Nombre de restaurants'},
        title="Nombre de restaurants Bon marché par ville"
    )
    st.plotly_chart(fig_bon_marche, use_container_width=True)
else:
    st.warning("Aucune donnée disponible pour les restaurants Bon marché.")

# Filtre interactif pour choisir une ville
ville_choisie = st.selectbox("Sélectionnez une ville pour afficher les notes moyennes par spécialité :", options=villes_selectionnees)

# Filtrer les données selon la ville choisie
data_ville_filtre = data_clean[data_clean['ville'] == ville_choisie]

# Exemple: recalculer le top spécialités pour cette ville seulement
counts_ville = data_ville_filtre.groupby('spécialité').size().reset_index(name='nombre')
top_specs_ville = counts_ville.sort_values(by='nombre', ascending=False).head(5)['spécialité'].tolist()

# Exemple: note moyenne par spécialité pour la ville choisie
note_par_spec_ville = (
    data_ville_filtre.dropna(subset=['notation'])
    .groupby('spécialité')['notation']
    .mean()
    .reset_index()
    .sort_values(by='notation', ascending=False)
)

# Afficher un graphique adapté
st.subheader(f"⭐ {ville_choisie}")
fig_note_ville = px.bar(
    note_par_spec_ville,
    x='spécialité',
    y='notation',
    color_discrete_sequence=['yellow'],
    labels={'notation': 'Note moyenne'},
    title=f"Note moyenne par spécialité - {ville_choisie}"
)
st.plotly_chart(fig_note_ville, use_container_width=True)

st.subheader("🏆 Pourcentage de restaurants très bien notés (≥ 4.5) par ville")

# Filtrer les données utiles
data_noted = data.dropna(subset=['notation'])
data_noted = data_noted[data_noted['ville'].isin(villes_selectionnees)]

# Total et bien notés par ville
total_par_ville = data_noted.groupby('ville').size()
bien_notes_par_ville = data_noted[data_noted['notation'] >= 4.5].groupby('ville').size()

# Calcul pourcentage
pourcentage_bien_notes = (bien_notes_par_ville / total_par_ville * 100).reset_index(name='pourcentage')
pourcentage_bien_notes = pourcentage_bien_notes.sort_values(by='pourcentage', ascending=False)

# Graphique
fig_pourcentage = px.bar(
    pourcentage_bien_notes,
    x='ville',
    y='pourcentage',
    color_discrete_sequence=['#2ca02c'],
    labels={'pourcentage': '% Restaurants ≥ 4.5'},
    title="🥇 Pourcentage de restaurants très bien notés (≥ 4.5) par ville"
)
fig_pourcentage.update_traces(text=pourcentage_bien_notes['pourcentage'].apply(lambda x: f"{x:.1f}%"), textposition='outside')
st.plotly_chart(fig_pourcentage, use_container_width=True)