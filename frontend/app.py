import streamlit as st
import requests  # Importar a biblioteca requests

# URL base da sua API Flask (certifique-se de que o servidor Flask está rodando!)
# Se o Flask estiver rodando em outro endereço/porta, ajuste aqui.
FLASK_API_BASE_URL = "http://127.0.0.1:5000"


# --- Funções para Interagir com a API Flask ---
def register_user_api(name, email, password, role="Usuário"):
    endpoint = f"{FLASK_API_BASE_URL}/register"
    payload = {"name": name, "email": email, "password": password, "role": role}
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()  # Levanta um erro para status de erro HTTP (4xx ou 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar com a API de registro: {e}")
        if response.status_code == 409:  # UniqueViolation
            return {"error": "Email já registrado."}
        return {"error": f"Erro na API de registro: {response.text}"}


def login_user_api(email, password):
    endpoint = f"{FLASK_API_BASE_URL}/login"
    payload = {"email": email, "password": password}
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()  # Levanta um erro para status de erro HTTP (4xx ou 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar com a API de login: {e}")
        if response.status_code == 401:  # Unauthorized
            return {"error": "Email ou senha inválidos."}
        return {"error": f"Erro na API de login: {response.text}"}


# --- Configurações da Página Streamlit ---
st.set_page_config(
    page_title="Software de Monitoramento de Obras",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Estilo CSS Personalizado (Baseado no Conceito Visual) ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #1a1a1a; /* Fundo cinza-escuro */
        color: #f0f2f6; /* Cor do texto principal */
        font-family: 'Poppins', sans-serif;
    }
    .stTextInput > div > div > input {
        background-color: #333333; /* Fundo dos campos de input */
        color: #f0f2f6;
        border-radius: 8px;
        border: 1px solid #555555;
        padding: 10px;
    }
    .stTextInput > label {
        color: #f0f2f6; /* Cor dos rótulos dos campos */
    }
    .stButton > button {
        background-color: #CF1219; /* Cor de destaque para botões */
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s;
    }
    .stButton > button:hover {
        background-color: #991B1B; /* Tom mais escuro no hover */
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #CF1219; /* Títulos em cor de destaque */
    }
    .login-container, .main-app-container {
        background-color: #2a2a2a; /* Fundo do container */
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        max-width: 450px;
        margin: 50px auto;
        text-align: center;
    }
    .logo-text {
        color: #CF1219;
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .logo-subtitle {
        color: #f0f2f6;
        font-size: 1.2em;
        margin-bottom: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Gerenciamento de Estado da Sessão ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "show_register" not in st.session_state:
    st.session_state.show_register = False


# --- Função para Exibir a Tela de Login ---
def show_login_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    st.markdown(
        '<div class="logo-text">Software<span style="color: #f0f2f6;">Obras</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="logo-subtitle">Gerenciamento Inteligente de Projetos de Construção</div>',
        unsafe_allow_html=True,
    )

    st.write("---")  # Linha divisória

    st.subheader("Login")

    email = st.text_input(
        "Email", placeholder="seu.email@exemplo.com", key="login_email"
    )
    password = st.text_input(
        "Senha", type="password", placeholder="********", key="login_password"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Entrar", key="login_button"):
            if email and password:
                result = login_user_api(email, password)
                if "user_id" in result:
                    st.session_state.logged_in = True
                    st.session_state.user_info = result
                    st.success(f"Bem-vindo, {result.get('user_name', 'usuário')}!")
                    st.rerun()  # Força o Streamlit a re-executar e mostrar a página principal
                else:
                    st.error(result.get("error", "Erro ao fazer login."))
            else:
                st.warning("Por favor, insira email e senha.")
    with col2:
        if st.button("Registrar", key="show_register_button"):
            st.session_state.show_register = True
            st.rerun()

    st.markdown(
        '<div style="margin-top: 20px; color: #888888;">Esqueceu sua senha? Clique aqui.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# --- Função para Exibir a Tela de Registro ---
def show_register_page():
    st.markdown(
        '<div class="login-container">', unsafe_allow_html=True
    )  # Reutilizando o estilo do container

    st.markdown(
        '<div class="logo-text">Software<span style="color: #f0f2f6;">Obras</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="logo-subtitle">Crie sua conta</div>', unsafe_allow_html=True
    )

    st.write("---")

    st.subheader("Registro")

    name = st.text_input("Nome Completo", key="register_name")
    email = st.text_input("Email", key="register_email")
    password = st.text_input("Senha", type="password", key="register_password")
    confirm_password = st.text_input(
        "Confirmar Senha", type="password", key="confirm_password"
    )

    if st.button("Criar Conta", key="create_account_button"):
        if password != confirm_password:
            st.error("As senhas não coincidem.")
        elif not name or not email or not password:
            st.warning("Por favor, preencha todos os campos.")
        else:
            result = register_user_api(name, email, password)
            if "id" in result:
                st.success("Conta criada com sucesso! Você pode fazer login agora.")
                st.session_state.show_register = False  # Volta para a tela de login
                st.rerun()
            else:
                st.error(result.get("error", "Erro ao criar conta."))

    if st.button("Voltar para Login", key="back_to_login_button"):
        st.session_state.show_register = False
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# --- Função para Exibir a Página Principal do Aplicativo (Após Login) ---
def show_main_app_page():
    st.markdown('<div class="main-app-container">', unsafe_allow_html=True)
    st.markdown(
        f"<h1>Bem-vindo, {st.session_state.user_info.get('user_name', 'Usuário')}!</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p>Seu nível de acesso: <strong>{st.session_state.user_info.get('user_role', 'Não definido')}</strong></p>",
        unsafe_allow_html=True,
    )
    st.write(
        "Esta é a página principal do seu software. Aqui você verá os dashboards e opções de gestão."
    )
    st.write("Em breve, integraremos os dados do seu back-end aqui!")

    if st.button("Sair", key="logout_button"):
        st.session_state.logged_in = False
        st.session_state.user_info = None
        st.session_state.show_register = (
            False  # Resetar para garantir que vai para login
        )
        st.rerun()

    # Adicione aqui os componentes e layouts das outras páginas (Painel, Projetos, etc.)
    # Por exemplo, você pode usar st.sidebar para navegação ou st.tabs
    st.subheader("Funcionalidades Disponíveis (Esqueleto)")
    st.write("- Painel de Visão Geral")
    st.write("- Gestão de Projetos")
    st.write("- Diário de Obra")
    st.write("- Relatórios")
    st.write("- Cadastros Base (Clientes, Equipe, Fornecedores, etc.)")

    st.markdown("</div>", unsafe_allow_html=True)


# --- Lógica Principal do Aplicativo ---
if st.session_state.logged_in:
    show_main_app_page()
elif st.session_state.show_register:
    show_register_page()
else:
    show_login_page()
