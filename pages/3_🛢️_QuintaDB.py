import streamlit as st

st.set_page_config(page_title="QuintaDB", page_icon="🛢️")

redirect_url = "https://quintadb.com/apps/bAcSo4W7PcQjKBDvldHmkk/portals/cdxSkMc8nlaRxdVxCJbmk4/login"

st.markdown(
    f"""
    <meta http-equiv="refresh" content="0; url={redirect_url}">
    """,
    unsafe_allow_html=True
)

st.write("Serás redirigido a QuintaDB...")