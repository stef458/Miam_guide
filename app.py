import streamlit as st
import duckdb
import pandas as pd
from dotenv import load_dotenv
import os
from geopy.distance import geodesic
from streamlit_javascript import st_javascript
import urllib.parse  
from geopy.geocoders import Nominatim

table_name= "restaurants_france_specialtiescompletdef"

# Chargement des variables d'environnement
load_dotenv()
token = os.getenv("mother_duck_token")


# Config page
st.set_page_config(page_title="Restaurants en France", layout="wide")

# Titre
st.markdown("""
<h1 style='font-size: 48px; margin-bottom: 0; border: 3px solid yellow; padding: 10px 20px; border-radius: 12px; display: inline-block;'>
    Miam Guide 🍔🍣🍕
</h1>
<p style='font-size: 20px; color: yellow; margin-top: 0;'>
    Trouvez votre restaurant préféré au plus près de vous !!! <span style='font-size: 48px;'>👨‍🍳</span>
</p>
""", unsafe_allow_html=True)

# Géolocalisation automatique
coords = st_javascript("""await new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            resolve({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude
            });
        },
        (err) => {
            resolve(null);
        }
    );
});""")

user_coords = None
if coords is None:
    st.info("📍 Cliquez sur 'Autoriser' dans le popup du navigateur pour activer la géolocalisation.")
elif isinstance(coords, dict) and "latitude" in coords:
    user_coords = (coords["latitude"], coords["longitude"])
    
    # Géocodage inverse avec Nominatim (OpenStreetMap)
    geolocator = Nominatim(user_agent="miam_guide_app")
    try:
        location = geolocator.reverse(user_coords, language='fr')
        if location and "address" in location.raw:
            ville_detectee = location.raw["address"].get("city") or \
                             location.raw["address"].get("town") or \
                             location.raw["address"].get("village") or \
                             location.raw["address"].get("municipality") or "Inconnue"
            st.success(f"📍 Position détectée : {ville_detectee}")
        else:
            st.success(f"📍 Position détectée : {user_coords} (ville inconnue)")
    except Exception as e:
        st.warning(f"📍 Coordonnées détectées : {user_coords} (erreur géolocalisation : {e})")

# Connexion à la DB
db_path = f"md:my_db?motherduck_token={token}"
con = duckdb.connect(db_path)

# Vérification des tables existantes
tables = con.execute("SHOW TABLES").fetchall()


# Valeurs uniques pour filtres
specialites = [s[0].strip() for s in con.execute(f'SELECT DISTINCT "spécialité" FROM {table_name} ORDER BY "spécialité"').fetchall()]
prix = [p[0].strip() for p in con.execute(f'SELECT DISTINCT "niveau de prix (libellé)" FROM {table_name} ORDER BY "niveau de prix (libellé)"').fetchall()]

# Filtres utilisateur
specialite_selection = st.selectbox("🥗 Choisissez une spécialité", ["Toutes"] + specialites)
note_min = st.slider("⭐ Note minimale", min_value=4.0, max_value=5.0, value=4.0, step=0.1)
prix_selection = st.selectbox("💰 Choisissez une fourchette de prix", ["Toutes"] + prix)

# Info parking
st.markdown("""
<div style="display: flex; align-items: center; margin-bottom: 20px;">
    <div style="font-size: 48px; margin-right: 10px;">
        ℹ️
    </div>
    <div style="
        border: 1px solid #FF8C00; 
        background-color: #FF8C00;  
        padding: 15px; 
        border-radius: 8px; 
        font-size: 24px; 
        color: black; 
        font-style: normal;
        flex-grow: 1;
    ">
        <span style="font-style: normal;">🅿️ 🚗</span> <span style="font-weight: bold; font-style: italic;">Information sur la présence de parkings à proximité non disponible pour le moment.</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Construction de la requête SQL
query = f"""
SELECT ville, "spécialité", "niveau de prix (libellé)", latitude, longitude, nom
FROM {table_name}
WHERE 1=1
"""
params_sql = []

if specialite_selection != "Toutes":
    query += ' AND TRIM("spécialité") = ?'
    params_sql.append(specialite_selection.strip())

if prix_selection != "Toutes":
    query += ' AND TRIM("niveau de prix (libellé)") = ?'
    params_sql.append(prix_selection.strip())

data = con.execute(query, tuple(params_sql)).fetchdf()

# Si coordonnées disponibles, filtrer par distance
if user_coords and not data.empty:
    rayon = st.slider("🔎 Rayon de recherche (km)", 1, 50, 10)
    data["distance_km"] = data.apply(
        lambda row: geodesic(user_coords, (row["latitude"], row["longitude"])).km
        if pd.notnull(row["latitude"]) and pd.notnull(row["longitude"]) else None,
        axis=1
    )
    data = data.sort_values("distance_km")
    data = data[data["distance_km"] <= rayon]
    st.success(f"Restaurants dans un rayon de {rayon} km : {len(data)}")
else:
    st.info(f"Restaurants trouvés avec les filtres : {len(data)}")

# Affichage liste des restaurants
if not data.empty:
    st.markdown("### Liste des restaurants correspondant à vos critères :")
    for idx, row in data.iterrows():
        nom = row["nom"]
        ville = row["ville"]
        specialite = row["spécialité"]
        prix = row["niveau de prix (libellé)"]
        lat = row["latitude"]
        lon = row["longitude"]
        dist = None
        if "distance_km" in data.columns:
            dist = round(row["distance_km"], 2)

        resto_info = f"**{nom}** - {ville} - {specialite} - {prix}"
        if dist is not None:
            resto_info += f" - {dist} km"

        st.write(resto_info)

        if user_coords and pd.notnull(lat) and pd.notnull(lon):
            origin = f"{user_coords[0]},{user_coords[1]}"
            destination = f"{lat},{lon}"
            url = f"https://www.google.com/maps/dir/?api=1&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(destination)}&travelmode=driving"
            st.markdown(f"[➡️ Itinéraire vers ce restaurant]({url})", unsafe_allow_html=True)

        st.markdown("---")

# Affichage tableau résumé
if not data.empty:
    if "distance_km" in data.columns:
        data_display = data[["nom", "ville", "spécialité", "niveau de prix (libellé)", "distance_km"]].copy()
        data_display["distance_km"] = data_display["distance_km"].round(2)
    else:
        data_display = data[["nom", "ville", "spécialité", "niveau de prix (libellé)"]]

    st.markdown("### Liste des restaurants correspondant à vos critères :")
    st.dataframe(data_display.reset_index(drop=True))

# Chat IA basique
st.markdown("---")
st.subheader("💬 Posez une question sur les restaurants")

if st.button("🪩 Effacer la conversation"):
    st.session_state["messages"] = []
    st.experimental_rerun()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("🤖 Posez une question, par exemple : Quel est le type de cuisine le plus courant à Lyon ?"):
    st.chat_message("user").write(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    villes = [v[0].strip() for v in con.execute(f"SELECT DISTINCT ville FROM {table_name} ORDER BY ville").fetchall()]
    ville_mentionnee = None
    prompt_lower = prompt.lower()
    for ville in villes:
        if ville.lower() in prompt_lower:
            ville_mentionnee = ville
            break

    if ville_mentionnee:
        top = con.execute(f"""
            SELECT "spécialité", COUNT(*) AS nb
            FROM {table_name}
            WHERE LOWER(TRIM(ville)) = ?
            GROUP BY "spécialité"
            ORDER BY nb DESC
            LIMIT 1
        """, (ville_mentionnee.lower(),)).fetchone()

        if top:
            response = f"🍽️ À {ville_mentionnee}, la spécialité la plus représentée est : **{top[0]}** avec {top[1]} restaurants."
        else:
            response = f"❌ Je n'ai trouvé aucune spécialité dans la base pour la ville **{ville_mentionnee}**."
    else:
        response = "⚠️ Je n'ai pas détecté de ville dans votre question. Merci de mentionner une ville connue."

    st.chat_message("assistant").write(response)
    st.session_state["messages"].append({"role": "assistant", "content": response})


