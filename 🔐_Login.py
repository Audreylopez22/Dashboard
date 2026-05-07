import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
st.set_page_config(page_title="Login", page_icon="👋", layout="wide")

st.title("🎓 Conecta Unicamacho")

with open("./config.yaml", "r") as file:
    config = yaml.load(file, Loader=SafeLoader)

#hashed_passwords = stauth.Hasher.hash_passwords(config["credentials"])
#st.write(hashed_passwords)

for i, username in enumerate(config["credentials"]["usernames"]):
    config["credentials"]["usernames"][username]["password"] = st.secrets.passwords[username]

plain_passwords = []


def main():
    if st.secrets.subscription.active:
        authenticator = stauth.Authenticate(
            config["credentials"],
            config["cookie"]["name"],
            config["cookie"]["key"],
            config["cookie"]["expiry_days"],
        )
        custom_labels = {
            'Form name': 'Inicio de sesión', # Spanish example
            'Username': 'Usuario',
            'Password': 'Contraseña',
            'Login': 'Entrar'
        }
        authenticator.login("main", fields=custom_labels)

        if st.session_state["authentication_status"]:
            st.write(f'Bienvenido *{st.session_state["name"]}*')
            authenticator.logout("Cerrar sesión", "main")
        elif st.session_state["authentication_status"] is False:
            st.error("Usuario o contraseña incorrectos")
        elif st.session_state["authentication_status"] is None:
            st.warning("Por favor para ingresar introduce tu usuario y contraseña")
    else:
        st.warning(
            "Your subscription is inactive. Please make the monthly payment to access the application."
        )


if __name__ == "__main__":
    main()
