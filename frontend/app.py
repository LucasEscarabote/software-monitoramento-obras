import streamlit as st
import psycopg2  # Importar o driver do PostgreSQL
from psycopg2.extras import RealDictCursor  # Para retornar resultados como dicionários
import os  # Importar para acessar variáveis de ambiente
from dotenv import load_dotenv  # Para carregar .env localmente
import bcrypt  # Para hash de senhas
# NÃO precisamos mais de PIL.Image para o logo SVG com esta abordagem
# from PIL import Image

# Carrega as variáveis de ambiente do arquivo .env se rodando localmente
try:
    load_dotenv()
except Exception:
    pass  # Ignora se .env não for encontrado (ex: no Streamlit Cloud)

# --- Conexão com o Banco de Dados ---
# A URL de conexão será lida de st.secrets no Streamlit Cloud
# Localmente, ela será lida do .env
DATABASE_URL = os.getenv("DATABASE_URL")


# Função que tenta estabelecer uma nova conexão (sem cache)
@st.cache_resource
def get_db_connection():
    if not DATABASE_URL:
        st.error(
            "Variável de ambiente DATABASE_URL não configurada. Verifique os Secrets do Streamlit Cloud ou seu arquivo .env."
        )
        st.stop()  # Para a execução do app se a conexão não puder ser estabelecida
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        st.error(
            f"Erro ao conectar ao banco de dados: {e}. Verifique a string de conexão."
        )
        st.stop()
    return None  # Deveria ser inalcançável devido ao st.stop()


# --- Funções de Manipulação do Banco de Dados (CRUD para todas as tabelas) ---
# Função auxiliar para executar operações de BD com gerenciamento de conexão
def execute_db_operation(func, *args, **kwargs):
    conn = None
    try:
        conn = get_db_connection()
        if conn:  # Garante que a conexão foi obtida com sucesso
            result = func(conn, *args, **kwargs)
            return result
    except Exception as e:
        st.error(f"Erro durante a operação de banco de dados: {e}")
        if conn:
            conn.rollback()  # Garante que a transação seja desfeita em caso de erro
    finally:
        # Em Streamlit com st.cache_resource, a conexão é gerenciada pelo cache.
        # Não fechamos explicitamente aqui para permitir reuso.
        pass
    return None


# Função para criar tabelas (executada na inicialização do app)
def _create_tables_if_not_exists(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name VARCHAR(255),
            role VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS suppliers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            cnpj_cpf VARCHAR(18),
            contact VARCHAR(255) NOT NULL,
            address TEXT,
            notes TEXT,
            delivery_time VARCHAR(100),
            payment_terms VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cost_categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS units_of_measure (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(50) NOT NULL UNIQUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS clients (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            contact VARCHAR(255),
            cnpj VARCHAR(18),
            address TEXT,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS team_members (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            role VARCHAR(100),
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20),
            cpf VARCHAR(14),
            hiring_date DATE,
            access_level VARCHAR(50),
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS projects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            client_id UUID NOT NULL,
            address TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'Em Planejamento',
            budget NUMERIC(15, 2) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS project_services (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            duration VARCHAR(50),
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            progress NUMERIC(5, 2) DEFAULT 0,
            cost NUMERIC(15, 2) NOT NULL,
            unit VARCHAR(50),
            measure NUMERIC(10, 2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS project_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(100),
            file_url TEXT,
            size_kb NUMERIC(10, 2),
            upload_date DATE DEFAULT CURRENT_DATE,
            uploaded_by UUID,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES team_members(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS document_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id UUID NOT NULL,
            version_number INT NOT NULL,
            file_url TEXT,
            upload_date DATE DEFAULT CURRENT_DATE,
            uploaded_by UUID,
            notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES project_documents(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES team_members(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS daily_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id UUID NOT NULL,
            log_date DATE NOT NULL,
            weather VARCHAR(100),
            personnel TEXT,
            notes TEXT,
            materials_received TEXT,
            equipment_used TEXT,
            occurrences TEXT,
            location_lat NUMERIC(10, 7),
            location_lon NUMERIC(10, 7),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS daily_log_activities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            daily_log_id UUID NOT NULL,
            step_name VARCHAR(255),
            activity_type VARCHAR(100),
            quantity NUMERIC(10, 2),
            unit VARCHAR(50),
            observations TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (daily_log_id) REFERENCES daily_logs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS daily_log_costs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            daily_log_id UUID NOT NULL,
            description TEXT NOT NULL,
            value NUMERIC(15, 2) NOT NULL,
            category VARCHAR(255),
            associated_step VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (daily_log_id) REFERENCES daily_logs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS daily_log_photos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            daily_log_id UUID NOT NULL,
            photo_url TEXT NOT NULL,
            description TEXT,
            upload_date DATE DEFAULT CURRENT_DATE,
            uploaded_by UUID,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (daily_log_id) REFERENCES daily_logs(id) ON DELETE CASCADE,
            FOREIGN KEY (uploaded_by) REFERENCES team_members(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS project_team_members (
            project_id UUID NOT NULL,
            team_member_id UUID NOT NULL,
            PRIMARY KEY (project_id, team_member_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (team_member_id) REFERENCES team_members(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
        # st.success("Tabelas verificadas/criadas com sucesso!") # Comentado para evitar flood de msg
    except Exception as e:
        st.error(f"Erro ao criar/verificar tabelas: {e}")
        conn.rollback()
    finally:
        if cur:
            cur.close()


def create_tables_if_not_exists_wrapper():
    execute_db_operation(_create_tables_if_not_exists)


# Chamar a função para criar tabelas (será executada na inicialização do app)
create_tables_if_not_exists_wrapper()


# --- AUTENTICAÇÃO ---
def register_user_db(name, email, password, role="Usuário"):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        # bcrypt.hashpw espera bytes, então codificamos a senha
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
        cur.execute(
            """INSERT INTO users (email, password_hash, name, role)
               VALUES (%s, %s, %s, %s) RETURNING id;""",
            (email, hashed_password, name, role),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Usuário registrado com sucesso", "id": str(user_id)}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "Email já registrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def login_user_db(email, password):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT id, email, password_hash, name, role FROM users WHERE email = %s;",
            (email,),
        )
        user = cur.fetchone()
        if user and bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("utf-8")
        ):
            return {
                "message": "Login bem-sucedido",
                "user_id": str(user["id"]),
                "user_name": user["name"],
                "user_role": user["role"],
            }
        else:
            return {"error": "Email ou senha inválidos."}
    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Fornecedores ---
def add_supplier_db(
    name,
    contact,
    cnpj_cpf=None,
    address=None,
    notes=None,
    delivery_time=None,
    payment_terms=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO suppliers (name, cnpj_cpf, contact, address, notes, delivery_time, payment_terms)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, cnpj_cpf, contact, address, notes, delivery_time, payment_terms),
        )
        supplier_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Fornecedor adicionado com sucesso", "id": str(supplier_id)}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_suppliers_db():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM suppliers ORDER BY name;")
        suppliers = cur.fetchall()
        return suppliers
    except Exception as e:
        st.error(f"Erro ao obter fornecedores: {e}")
        return []
    finally:
        cur.close()


def update_supplier_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = (
            f"UPDATE suppliers SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        )
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Fornecedor atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Fornecedor não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_supplier_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM suppliers WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Fornecedor deletado com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Fornecedor não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Categorias de Custo ---
def add_cost_category_db(name, description=None):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO cost_categories (name, description)
               VALUES (%s, %s) RETURNING id;""",
            (name, description),
        )
        category_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Categoria de custo adicionada com sucesso",
            "id": str(category_id),
        }
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "Categoria com este nome já existe."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_cost_categories_db():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM cost_categories ORDER BY name;")
        categories = cur.fetchall()
        return categories
    except Exception as e:
        st.error(f"Erro ao obter categorias de custo: {e}")
        return []
    finally:
        cur.close()


def update_cost_category_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE cost_categories SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Categoria de custo atualizada com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Categoria de custo não encontrada."}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "Categoria com este nome já existe."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_cost_category_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM cost_categories WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Categoria de custo deletada com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Categoria de custo não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Unidades de Medida ---
def add_unit_of_measure_db(name):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO units_of_measure (name)
               VALUES (%s) RETURNING id;""",
            (name,),
        )
        unit_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Unidade de medida adicionada com sucesso",
            "id": str(unit_id),
        }
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "Unidade de medida com este nome já existe."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_units_of_measure_db():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM units_of_measure ORDER BY name;")
        units = cur.fetchall()
        return units
    except Exception as e:
        st.error(f"Erro ao obter unidades de medida: {e}")
        return []
    finally:
        cur.close()


def update_unit_of_measure_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE units_of_measure SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Unidade de medida atualizada com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Unidade de medida não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_unit_of_measure_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM units_of_measure WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Unidade de medida deletada com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Unidade de medida não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Clientes ---
def add_client_db(name, contact=None, cnpj=None, address=None, notes=None):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO clients (name, contact, cnpj, address, notes)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (name, contact, cnpj, address, notes),
        )
        client_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Cliente adicionado com sucesso", "id": str(client_id)}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_clients_db():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM clients ORDER BY name;")
        clients = cur.fetchall()
        return clients
    except Exception as e:
        st.error(f"Erro ao obter clientes: {e}")
        return []
    finally:
        cur.close()


def update_client_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = (
            f"UPDATE clients SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        )
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Cliente atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Cliente não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_client_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM clients WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {"message": "Cliente deletado com sucesso", "id": str(deleted_id[0])}
        return {"error": "Cliente não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Membros da Equipe ---
def add_team_member_db(
    name,
    email,
    role=None,
    phone=None,
    cpf=None,
    hiring_date=None,
    access_level=None,
    notes=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO team_members (name, role, email, phone, cpf, hiring_date, access_level, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, role, email, phone, cpf, hiring_date, access_level, notes),
        )
        member_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Membro da equipe adicionado com sucesso",
            "id": str(member_id),
        }
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "Email já registrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_team_members_db():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT * FROM team_members ORDER BY name;")
        members = cur.fetchall()
        return members
    except Exception as e:
        st.error(f"Erro ao obter membros da equipe: {e}")
        return []
    finally:
        cur.close()


def update_team_member_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE team_members SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Membro da equipe atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Membro da equipe não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_team_member_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM team_members WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Membro da equipe deletado com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Membro da equipe não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Projetos ---
def add_project_db(
    name,
    client_id,
    address,
    start_date,
    end_date,
    status="Em Planejamento",
    budget=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO projects (name, client_id, address, start_date, end_date, status, budget)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, client_id, address, start_date, end_date, status, budget),
        )
        project_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Projeto adicionado com sucesso", "id": str(project_id)}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_projects_db():
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT p.*, c.name as client_name
            FROM projects p
            JOIN clients c ON p.client_id = c.id
            ORDER BY p.name;
        """)
        projects = cur.fetchall()
        return projects
    except Exception as e:
        st.error(f"Erro ao obter projetos: {e}")
        return []
    finally:
        cur.close()


def get_project_db(id):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT p.*, c.name as client_name
            FROM projects p
            JOIN clients c ON p.client_id = c.id
            WHERE p.id = %s;
        """,
            (id,),
        )
        project = cur.fetchone()
        return project
    except Exception as e:
        st.error(f"Erro ao obter projeto: {e}")
        return None
    finally:
        cur.close()


def update_project_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = (
            f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        )
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Projeto atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Projeto não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_project_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM projects WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {"message": "Projeto deletado com sucesso", "id": str(deleted_id[0])}
        return {"error": "Projeto não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Serviços/Tarefas do Projeto ---
def add_project_service_db(
    project_id,
    name,
    duration,
    start_date,
    end_date,
    progress=0,
    cost=None,
    unit=None,
    measure=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO project_services (project_id, name, duration, start_date, end_date, progress, cost, unit, measure)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (
                project_id,
                name,
                duration,
                start_date,
                end_date,
                progress,
                cost,
                unit,
                measure,
            ),
        )
        service_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Serviço do projeto adicionado com sucesso",
            "id": str(service_id),
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_project_services_db(project_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if project_id:
            cur.execute(
                "SELECT * FROM project_services WHERE project_id = %s ORDER BY name;",
                (project_id,),
            )
        else:
            cur.execute("SELECT * FROM project_services ORDER BY name;")
        services = cur.fetchall()
        return services
    except Exception as e:
        st.error(f"Erro ao obter serviços do projeto: {e}")
        return []
    finally:
        cur.close()


def update_project_service_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE project_services SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Serviço do projeto atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Serviço do projeto não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_project_service_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM project_services WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Serviço do projeto deletado com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Serviço do projeto não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Documentos do Projeto ---
def add_project_document_db(
    project_id,
    name,
    doc_type,
    file_url,
    size_kb=None,
    upload_date=None,
    uploaded_by=None,
    notes=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO project_documents (project_id, name, type, file_url, size_kb, upload_date, uploaded_by, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (
                project_id,
                name,
                doc_type,
                file_url,
                size_kb,
                upload_date,
                uploaded_by,
                notes,
            ),
        )
        document_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Documento do projeto adicionado com sucesso",
            "id": str(document_id),
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_project_documents_db(project_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if project_id:
            cur.execute(
                "SELECT * FROM project_documents WHERE project_id = %s ORDER BY name;",
                (project_id,),
            )
        else:
            cur.execute("SELECT * FROM project_documents ORDER BY name;")
        documents = cur.fetchall()
        return documents
    except Exception as e:
        st.error(f"Erro ao obter documentos do projeto: {e}")
        return []
    finally:
        cur.close()


def update_project_document_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            if (
                key == "doc_type"
            ):  # 'type' é palavra reservada em Python, mapear para 'type' do DB
                set_clauses.append("type = %s")
            else:
                set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE project_documents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Documento do projeto atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Documento do projeto não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_project_document_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM project_documents WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Documento do projeto deletado com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Documento do projeto não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Versões de Documentos ---
def add_document_version_db(
    document_id,
    version_number,
    file_url,
    upload_date=None,
    uploaded_by=None,
    notes=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO document_versions (document_id, version_number, file_url, upload_date, uploaded_by, notes)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (document_id, version_number, file_url, upload_date, uploaded_by, notes),
        )
        version_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Versão do documento adicionada com sucesso",
            "id": str(version_id),
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_document_versions_db(document_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if document_id:
            cur.execute(
                "SELECT * FROM document_versions WHERE document_id = %s ORDER BY version_number DESC;",
                (document_id,),
            )
        else:
            cur.execute("SELECT * FROM document_versions ORDER BY created_at DESC;")
        versions = cur.fetchall()
        return versions
    except Exception as e:
        st.error(f"Erro ao obter versões de documentos: {e}")
        return []
    finally:
        cur.close()


def update_document_version_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE document_versions SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Versão do documento atualizada com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Versão do documento não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_document_version_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM document_versions WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Versão do documento deletada com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Versão do documento não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Diários de Obra (RDOs) ---
def add_daily_log_db(
    project_id,
    log_date,
    weather=None,
    personnel=None,
    notes=None,
    materials_received=None,
    equipment_used=None,
    occurrences=None,
    location_lat=None,
    location_lon=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO daily_logs (project_id, log_date, weather, personnel, notes, materials_received, equipment_used, occurrences, location_lat, location_lon)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (
                project_id,
                log_date,
                weather,
                personnel,
                notes,
                materials_received,
                equipment_used,
                occurrences,
                location_lat,
                location_lon,
            ),
        )
        log_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Diário de obra adicionado com sucesso", "id": str(log_id)}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_daily_logs_db(project_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if project_id:
            cur.execute(
                "SELECT * FROM daily_logs WHERE project_id = %s ORDER BY log_date DESC;",
                (project_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_logs ORDER BY log_date DESC;")
        logs = cur.fetchall()
        return logs
    except Exception as e:
        st.error(f"Erro ao obter diários de obra: {e}")
        return []
    finally:
        cur.close()


def update_daily_log_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE daily_logs SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Diário de obra atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Diário de obra não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_daily_log_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM daily_logs WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Diário de obra deletado com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Diário de obra não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Atividades do RDO ---
def add_daily_log_activity_db(
    daily_log_id,
    step_name,
    activity_type=None,
    quantity=None,
    unit=None,
    observations=None,
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO daily_log_activities (daily_log_id, step_name, activity_type, quantity, unit, observations)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (daily_log_id, step_name, activity_type, quantity, unit, observations),
        )
        activity_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Atividade do diário de obra adicionada com sucesso",
            "id": str(activity_id),
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_daily_log_activities_db(daily_log_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if daily_log_id:
            cur.execute(
                "SELECT * FROM daily_log_activities WHERE daily_log_id = %s ORDER BY created_at DESC;",
                (daily_log_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_log_activities ORDER BY created_at DESC;")
        activities = cur.fetchall()
        return activities
    except Exception as e:
        st.error(f"Erro ao obter atividades do diário de obra: {e}")
        return []
    finally:
        cur.close()


def update_daily_log_activity_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE daily_log_activities SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Atividade do diário de obra atualizada com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Atividade do diário de obra não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_daily_log_activity_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM daily_log_activities WHERE id = %s RETURNING id;", (id,)
        )
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Atividade do diário de obra deletada com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Atividade do diário de obra não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Custos do RDO ---
def add_daily_log_cost_db(
    daily_log_id, description, value, category=None, associated_step=None
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO daily_log_costs (daily_log_id, description, value, category, associated_step)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (daily_log_id, description, value, category, associated_step),
        )
        cost_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Custo do diário de obra adicionado com sucesso",
            "id": str(cost_id),
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_daily_log_costs_db(daily_log_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if daily_log_id:
            cur.execute(
                "SELECT * FROM daily_log_costs WHERE daily_log_id = %s ORDER BY created_at DESC;",
                (daily_log_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_log_costs ORDER BY created_at DESC;")
        costs = cur.fetchall()
        return costs
    except Exception as e:
        st.error(f"Erro ao obter custos do diário de obra: {e}")
        return []
    finally:
        cur.close()


def update_daily_log_cost_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE daily_log_costs SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Custo do diário de obra atualizado com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Custo do diário de obra não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_daily_log_cost_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM daily_log_costs WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Custo do diário de obra deletado com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Custo do diário de obra não encontrado."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Fotos do RDO ---
def add_daily_log_photo_db(
    daily_log_id, photo_url, description=None, upload_date=None, uploaded_by=None
):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO daily_log_photos (daily_log_id, photo_url, description, upload_date, uploaded_by)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (daily_log_id, photo_url, description, upload_date, uploaded_by),
        )
        photo_id = cur.fetchone()[0]
        conn.commit()
        return {
            "message": "Foto do diário de obra adicionada com sucesso",
            "id": str(photo_id),
        }
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_daily_log_photos_db(daily_log_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if daily_log_id:
            cur.execute(
                "SELECT * FROM daily_log_photos WHERE daily_log_id = %s ORDER BY upload_date DESC;",
                (daily_log_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_log_photos ORDER BY upload_date DESC;")
        photos = cur.fetchall()
        return photos
    except Exception as e:
        st.error(f"Erro ao obter fotos do diário de obra: {e}")
        return []
    finally:
        cur.close()


def update_daily_log_photo_db(id, updates):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        set_clauses = []
        values = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        if not set_clauses:
            return {"error": "Nenhum dado fornecido para atualização."}

        values.append(id)
        query = f"UPDATE daily_log_photos SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        if updated_id:
            return {
                "message": "Foto do diário de obra atualizada com sucesso",
                "id": str(updated_id[0]),
            }
        return {"error": "Foto do diário de obra não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def delete_daily_log_photo_db(id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM daily_log_photos WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        if deleted_id:
            return {
                "message": "Foto do diário de obra deletada com sucesso",
                "id": str(deleted_id[0]),
            }
        return {"error": "Foto do diário de obra não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Funções CRUD para Associação Projeto-Equipe ---
def add_project_team_member_db(project_id, team_member_id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO project_team_members (project_id, team_member_id)
               VALUES (%s, %s) RETURNING project_id, team_member_id;""",
            (project_id, team_member_id),
        )
        assigned_ids = cur.fetchone()
        conn.commit()
        return {
            "message": "Associação projeto-equipe adicionada com sucesso",
            "project_id": str(assigned_ids[0]),
            "team_member_id": str(assigned_ids[1]),
        }
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return {"error": "Associação já existe."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


def get_project_team_members_db(project_id=None, team_member_id=None):
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if project_id and team_member_id:
            cur.execute(
                "SELECT * FROM project_team_members WHERE project_id = %s AND team_member_id = %s;",
                (project_id, team_member_id),
            )
        elif project_id:
            cur.execute(
                "SELECT * FROM project_team_members WHERE project_id = %s;",
                (project_id,),
            )
        elif team_member_id:
            cur.execute(
                "SELECT * FROM project_team_members WHERE team_member_id = %s;",
                (team_member_id,),
            )
        else:
            cur.execute("SELECT * FROM project_team_members;")
        associations = cur.fetchall()
        return associations
    except Exception as e:
        st.error(f"Erro ao obter associações projeto-equipe: {e}")
        return []
    finally:
        cur.close()


def delete_project_team_member_db(project_id, team_member_id):
    conn = get_db_connection()
    if not conn:
        return {"error": "Sem conexão com o BD."}
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM project_team_members WHERE project_id = %s AND team_member_id = %s RETURNING project_id, team_member_id;",
            (project_id, team_member_id),
        )
        deleted_ids = cur.fetchone()
        conn.commit()
        if deleted_ids:
            return {
                "message": "Associação projeto-equipe deletada com sucesso",
                "project_id": str(deleted_ids[0]),
                "team_member_id": str(deleted_ids[1]),
            }
        return {"error": "Associação projeto-equipe não encontrada."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()


# --- Configurações da Página Streamlit (Continuação) ---
st.set_page_config(
    page_title="Software de Monitoramento de Obras",
    page_icon="🏗️",
    layout="wide",  # Alterado para wide para melhor layout com duas colunas
    initial_sidebar_state="collapsed",
)

# --- Estilo CSS Personalizado (Baseado no Conceito Visual) ---
st.markdown(
    """
    <style>
    /* Esconde o cabeçalho e rodapé padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stApp {
        background-color: #1a1a1a; /* Fundo escuro padrão */
        color: #f0f2f6; /* Cor do texto principal */
        font-family: 'Poppins', sans-serif;
        /* Removido background-image daqui para usar no container específico */
    }

    /* Container principal para dividir a tela em duas colunas */
    .main-layout-container {
        display: flex;
        min-height: 100vh; /* Garante que o container ocupe toda a altura da tela */
        width: 100vw; /* Ocupa toda a largura da viewport */
        margin: -1rem; /* Remove margens padrão do Streamlit */
        padding: 0; /* Remove padding padrão do Streamlit */
    }

    /* Coluna da esquerda para a imagem de fundo */
    .image-column {
        flex: 1; /* Ocupa metade do espaço */
        background-image: url("https://raw.githubusercontent.com/LucasEscarabote/software-monitoramento-obras/main/assets/login_background.jpg");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        border-top-right-radius: 15px; /* Borda arredondada superior direita */
        border-bottom-right-radius: 15px; /* Borda arredondada inferior direita */
        overflow: hidden; /* Garante que a imagem não vaze */
    }

    /* Coluna da direita para o formulário de login */
    .login-form-column {
        flex: 1; /* Ocupa metade do espaço */
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: white; /* Fundo branco para a coluna do formulário */
        padding: 20px;
    }

    .login-container {
        background-color: white; /* Fundo branco para o container de login */
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1); /* Sombra mais suave */
        max-width: 450px;
        width: 100%; /* Ocupa a largura total da coluna */
        text-align: center;
        color: #333333; /* Cor do texto padrão para o container branco */
    }

    .stTextInput > div > div > input {
        background-color: #f0f2f6; /* Fundo dos campos de input mais claro */
        color: #333333;
        border-radius: 8px;
        border: 1px solid #cccccc; /* Borda mais clara */
        padding: 10px;
    }
    .stTextInput > label {
        color: #333333; /* Cor dos rótulos dos campos */
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
    .logo-img {
        max-width: 150px; /* Ajuste o tamanho do logo */
        height: auto;
        margin-bottom: 20px;
    }
    .logo-text { /* Mantido para fallback */
        color: #CF1219;
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .logo-subtitle {
        color: #555555; /* Subtítulo mais suave no fundo claro */
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
    # Estrutura de duas colunas para o layout da imagem de fundo e formulário
    st.markdown('<div class="main-layout-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="image-column"></div>', unsafe_allow_html=True
    )  # Coluna da imagem

    st.markdown(
        '<div class="login-form-column">', unsafe_allow_html=True
    )  # Coluna do formulário
    st.markdown(
        '<div class="login-container">', unsafe_allow_html=True
    )  # Container do formulário dentro da coluna

    # Adiciona o logo aqui (SVG injetado diretamente)
    # Caminho para o arquivo SVG no GitHub
    logo_svg_url = "https://raw.githubusercontent.com/LucasEscarabote/software-monitoramento-obras/main/assets/logo.svg"
    st.markdown(
        f'<img src="{logo_svg_url}" class="logo-img" alt="Logo">',
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
                result = login_user_db(email, password)  # Chama a função DB diretamente
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

    st.markdown("</div>", unsafe_allow_html=True)  # Fecha login-container
    st.markdown("</div>", unsafe_allow_html=True)  # Fecha login-form-column
    st.markdown("</div>", unsafe_allow_html=True)  # Fecha main-layout-container


# --- Função para Exibir a Tela de Registro ---
def show_register_page():
    st.markdown('<div class="main-layout-container">', unsafe_allow_html=True)
    st.markdown(
        '<div class="image-column"></div>', unsafe_allow_html=True
    )  # Coluna da imagem

    st.markdown(
        '<div class="login-form-column">', unsafe_allow_html=True
    )  # Coluna do formulário
    st.markdown(
        '<div class="login-container">', unsafe_allow_html=True
    )  # Container do formulário dentro da coluna

    # Adiciona o logo aqui (SVG injetado diretamente)
    logo_svg_url = "https://raw.githubusercontent.com/LucasEscarabote/software-monitoramento-obras/main/assets/logo.svg"
    st.markdown(
        f'<img src="{logo_svg_url}" class="logo-img" alt="Logo">',
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
            result = register_user_db(
                name, email, password
            )  # Chama a função DB diretamente
            if "id" in result:
                st.success("Conta criada com sucesso! Você pode fazer login agora.")
                st.session_state.show_register = False  # Volta para a tela de login
                st.rerun()
            else:
                st.error(result.get("error", "Erro ao criar conta."))

    if st.button("Voltar para Login", key="back_to_login_button"):
        st.session_state.show_register = False
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # Fecha login-container
    st.markdown("</div>", unsafe_allow_html=True)  # Fecha login-form-column
    st.markdown("</div>", unsafe_allow_html=True)  # Fecha main-layout-container


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
