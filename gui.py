import streamlit as st
import requests
import json
from datetime import datetime

# --- Configuration de la page ---
st.set_page_config(
    page_title="Whooshy",
    page_icon="🔎",
    layout="centered"
)

# --- Style CSS personnalisé pour l'interface ---
st.markdown("""
<style>
/* Centrer le titre et le champ de recherche */
.st-emotion-cache-183-b, .st-emotion-cache-v0651h {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}
.st-emotion-cache-1215r6w{
    max-width: 600px;
}
.st-emotion-cache-10-b {
    max-width: 600px;
}

/* Style de la barre de recherche */
.st-emotion-cache-13-u input[type="text"] {
    font-size: 1.2rem;
    padding: 10px;
    border-radius: 20px;
    border: 2px solid #0068C9;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* Style des résultats de recherche */
.result-card {
    background-color: #f0f2f6;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 15px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s;
}

.result-card:hover {
    transform: translateY(-5px);
}

.result-title {
    color: #0068C9 !important;
    font-size: 1.3rem;
    font-weight: bold;
    text-decoration: none;
}

.result-url {
    color: #008000;
    font-size: 0.9rem;
}

.result-snippet {
    color: #333;
    font-size: 1rem;
}

.result-date {
    font-size: 0.8rem;
    color: #888;
    margin-top: 5px;
}
</style>
""", unsafe_allow_html=True)



# Crée une ligne pour le champ de recherche
search_col, _ = st.columns([1, 0.2])
with search_col:
    st.image("resources/whooshy_logo.png")
    query = st.text_input("Rechercher sur le web", placeholder="Ex: intelligence artificielle", label_visibility="hidden")

if query:
    try:
        # Affichage du spinner de chargement
        with st.spinner("Recherche en cours..."):
            response = requests.get(f"http://localhost:8000/search?q={query}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Gestion des dates
            def format_date(date_str):
                try:
                    dt = datetime.fromisoformat(date_str)
                    return dt.strftime("%d %B %Y")
                except ValueError:
                    return date_str

            st.subheader(f"Résultats pour : **{query}** ({data['count']} résultats)")
            st.write("---")
            
            for result in data["results"]:
                # Utilisation de st.markdown avec du HTML pour un meilleur rendu
                result_html = f"""
                <div class="result-card">
                    <a href="{result['url']}" class="result-title" target="_blank">{result['title']}</a><br>
                    <span class="result-url">{result['url']}</span>
                    <p class="result-snippet">{result['snippet']}</p>
                    <span class="result-date">Dernière mise à jour: {format_date(result['crawled_date'])}</span>
                </div>
                """
                st.markdown(result_html, unsafe_allow_html=True)

        else:
            st.error(f"Erreur lors de la recherche : {response.text}")

    except Exception as e:
        st.error(f"Erreur : {str(e)}")

# Pied de page (en option)
st.markdown("---")
st.markdown("Whooshy Searcher - Créé avec ❤ par Asmokz & Goatzer")