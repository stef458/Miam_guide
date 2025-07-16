import streamlit as st
from streamlit_javascript import st_javascript

st.set_page_config(page_title="Ma position", page_icon="📍")
st.title("📍 Obtenir ma position actuelle")

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

# Affichage du résultat
if coords is None:
    st.warning("❌ Position non autorisée ou indisponible.")
elif isinstance(coords, dict):
    st.success("✅ Position détectée :")
    st.write(f"Latitude : {coords['latitude']}")
    st.write(f"Longitude : {coords['longitude']}")
else:
    st.info("👉 Cliquez sur 'Autoriser' dans le popup de votre navigateur.")