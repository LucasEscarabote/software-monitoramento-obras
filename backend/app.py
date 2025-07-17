import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor  # Para retornar resultados como dicionários
from flask_bcrypt import Bcrypt  # Importar Bcrypt
from flask_cors import CORS  # Importar CORS para permitir requisições do frontend

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)  # Habilitar CORS para todas as rotas
bcrypt = Bcrypt(app)  # Inicializar Bcrypt

# Obtém a Connection String do Neon do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")


# Função auxiliar para obter conexão com o banco de dados
def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada no .env")
    conn = psycopg2.connect(DATABASE_URL)
    return conn


# Rota de teste para verificar a conexão com o banco de dados
@app.route("/test_db_connection")
def test_db_connection():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify(
            {
                "status": "success",
                "message": f"Conexão com o banco de dados bem-sucedida! Versão: {db_version[0]}",
            }
        ), 200
    except Exception as e:
        return jsonify(
            {
                "status": "error",
                "message": f"Falha na conexão com o banco de dados: {str(e)}",
            }
        ), 500


# Rota de teste simples para verificar se o Flask está funcionando
@app.route("/")
def home():
    return "Bem-vindo à API do Software de Monitoramento de Obras!"


# ----------------------------------------------------------------------
# AUTENTICAÇÃO
# ----------------------------------------------------------------------


@app.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    role = data.get("role", "Usuário")  # Default role

    if not email or not password:
        return jsonify({"error": "Email e senha são obrigatórios"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (email, password_hash, name, role)
               VALUES (%s, %s, %s, %s) RETURNING id;""",
            (email, hashed_password, name, role),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Usuário registrado com sucesso", "id": str(user_id)}
        ), 201
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "Email já registrado"}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/login", methods=["POST"])
def login_user():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email e senha são obrigatórios"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, email, password_hash, name, role FROM users WHERE email = %s;",
            (email,),
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and bcrypt.check_password_hash(user["password_hash"], password):
            # Autenticação bem-sucedida. Em uma aplicação real, aqui você geraria um token JWT.
            # Por simplicidade, vamos retornar o ID e o role do usuário.
            return jsonify(
                {
                    "message": "Login bem-sucedido",
                    "user_id": str(user["id"]),
                    "user_name": user["name"],
                    "user_role": user["role"],
                }
            ), 200
        else:
            return jsonify({"error": "Email ou senha inválidos"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------------------
# MÓDULO 0 - CADASTROS BASE (Já implementados, mas incluídos para completude)
# Funções para gerenciar Fornecedores, Categorias de Custo e Unidades de Medida
# ----------------------------------------------------------------------


# --- Rotas para Fornecedores ---
@app.route("/suppliers", methods=["POST"])
def add_supplier():
    data = request.get_json()
    name = data.get("name")
    contact = data.get("contact")
    cnpj_cpf = data.get("cnpj_cpf")
    address = data.get("address")
    notes = data.get("notes")
    delivery_time = data.get("delivery_time")
    payment_terms = data.get("payment_terms")

    if not name or not contact:
        return jsonify({"error": "Nome e contato são obrigatórios"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO suppliers (name, cnpj_cpf, contact, address, notes, delivery_time, payment_terms)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, cnpj_cpf, contact, address, notes, delivery_time, payment_terms),
        )
        supplier_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Fornecedor adicionado com sucesso", "id": str(supplier_id)}
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/suppliers", methods=["GET"])
def get_suppliers():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM suppliers ORDER BY name;")
        suppliers = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(suppliers), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/suppliers/<id>", methods=["PUT"])
def update_supplier(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE suppliers SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Fornecedor atualizado com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Fornecedor não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/suppliers/<id>", methods=["DELETE"])
def delete_supplier(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM suppliers WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {"message": "Fornecedor deletado com sucesso", "id": str(deleted_id[0])}
            ), 200
        return jsonify({"error": "Fornecedor não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Rotas para Categorias de Custo ---
@app.route("/cost_categories", methods=["POST"])
def add_cost_category():
    data = request.get_json()
    name = data.get("name")
    description = data.get("description")

    if not name:
        return jsonify({"error": "Nome da categoria é obrigatório"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO cost_categories (name, description)
               VALUES (%s, %s) RETURNING id;""",
            (name, description),
        )
        category_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Categoria de custo adicionada com sucesso",
                "id": str(category_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cost_categories", methods=["GET"])
def get_cost_categories():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM cost_categories ORDER BY name;")
        categories = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(categories), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cost_categories/<id>", methods=["PUT"])
def update_cost_category(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE cost_categories SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Categoria de custo atualizada com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Categoria de custo não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cost_categories/<id>", methods=["DELETE"])
def delete_cost_category(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cost_categories WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Categoria de custo deletada com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Categoria de custo não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --- Rotas para Unidades de Medida ---
@app.route("/units_of_measure", methods=["POST"])
def add_unit_of_measure():
    data = request.get_json()
    name = data.get("name")

    if not name:
        return jsonify({"error": "Nome da unidade de medida é obrigatório"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO units_of_measure (name)
               VALUES (%s) RETURNING id;""",
            (name,),  # (name,) é necessário para tuplas de um elemento
        )
        unit_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Unidade de medida adicionada com sucesso", "id": str(unit_id)}
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/units_of_measure", methods=["GET"])
def get_units_of_measure():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM units_of_measure ORDER BY name;")
        units = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(units), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/units_of_measure/<id>", methods=["PUT"])
def update_unit_of_measure(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE units_of_measure SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Unidade de medida atualizada com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Unidade de medida não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/units_of_measure/<id>", methods=["DELETE"])
def delete_unit_of_measure(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM units_of_measure WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Unidade de medida deletada com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Unidade de medida não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------------------
# MÓDULO 1 - GESTÃO DE OBRAS (Novas APIs)
# ----------------------------------------------------------------------


# --- Rotas para Clientes ---
@app.route("/clients", methods=["POST"])
def add_client():
    data = request.get_json()
    name = data.get("name")
    contact = data.get("contact")
    cnpj = data.get("cnpj")
    address = data.get("address")
    notes = data.get("notes")

    if not name:
        return jsonify({"error": "Nome do cliente é obrigatório"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO clients (name, contact, cnpj, address, notes)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (name, contact, cnpj, address, notes),
        )
        client_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Cliente adicionado com sucesso", "id": str(client_id)}
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clients", methods=["GET"])
def get_clients():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM clients ORDER BY name;")
        clients = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(clients), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clients/<id>", methods=["PUT"])
def update_client(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE clients SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {"message": "Cliente atualizado com sucesso", "id": str(updated_id[0])}
            ), 200
        return jsonify({"error": "Cliente não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clients/<id>", methods=["DELETE"])
def delete_client(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM clients WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {"message": "Cliente deletado com sucesso", "id": str(deleted_id[0])}
            ), 200
        return jsonify({"error": "Cliente não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Membros da Equipe ---


@app.route("/team_members", methods=["POST"])
def add_team_member():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    role = data.get("role")
    phone = data.get("phone")
    cpf = data.get("cpf")
    hiring_date = data.get("hiring_date")
    access_level = data.get("access_level")
    notes = data.get("notes")

    if not name or not email:
        return jsonify(
            {"error": "Nome e email do membro da equipe são obrigatórios"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO team_members (name, role, email, phone, cpf, hiring_date, access_level, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, role, email, phone, cpf, hiring_date, access_level, notes),
        )
        member_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Membro da equipe adicionado com sucesso", "id": str(member_id)}
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/team_members", methods=["GET"])
def get_team_members():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM team_members ORDER BY name;")
        members = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(members), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/team_members/<id>", methods=["PUT"])
def update_team_member(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = (
        f"UPDATE team_members SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
    )

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Membro da equipe atualizado com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Membro da equipe não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/team_members/<id>", methods=["DELETE"])
def delete_team_member(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM team_members WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Membro da equipe deletado com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Membro da equipe não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Projetos ---


@app.route("/projects", methods=["POST"])
def add_project():
    data = request.get_json()
    name = data.get("name")
    client_id = data.get("client_id")
    address = data.get("address")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    status = data.get("status", "Em Planejamento")  # Default status
    budget = data.get("budget")

    if (
        not name
        or not client_id
        or not address
        or not start_date
        or not end_date
        or budget is None
    ):
        return jsonify({"error": "Campos obrigatórios do projeto ausentes"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO projects (name, client_id, address, start_date, end_date, status, budget)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
            (name, client_id, address, start_date, end_date, status, budget),
        )
        project_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Projeto adicionado com sucesso", "id": str(project_id)}
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/projects", methods=["GET"])
def get_projects():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # JOIN com clients para trazer o nome do cliente
        cur.execute("""
            SELECT p.*, c.name as client_name
            FROM projects p
            JOIN clients c ON p.client_id = c.id
            ORDER BY p.name;
        """)
        projects = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/projects/<id>", methods=["GET"])
def get_project(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
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
        cur.close()
        conn.close()
        if project:
            return jsonify(project), 200
        return jsonify({"error": "Projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/projects/<id>", methods=["PUT"])
def update_project(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {"message": "Projeto atualizado com sucesso", "id": str(updated_id[0])}
            ), 200
        return jsonify({"error": "Projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/projects/<id>", methods=["DELETE"])
def delete_project(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM projects WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {"message": "Projeto deletado com sucesso", "id": str(deleted_id[0])}
            ), 200
        return jsonify({"error": "Projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Serviços/Tarefas do Projeto ---


@app.route("/project_services", methods=["POST"])
def add_project_service():
    data = request.get_json()
    project_id = data.get("project_id")
    name = data.get("name")
    duration = data.get("duration")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    progress = data.get("progress", 0)
    cost = data.get("cost")
    unit = data.get("unit")
    measure = data.get("measure")

    if not project_id or not name or not start_date or not end_date or cost is None:
        return jsonify(
            {"error": "Campos obrigatórios do serviço do projeto ausentes"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Serviço do projeto adicionado com sucesso",
                "id": str(service_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_services", methods=["GET"])
def get_project_services():
    project_id = request.args.get("project_id")  # Permite filtrar por project_id
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if project_id:
            cur.execute(
                "SELECT * FROM project_services WHERE project_id = %s ORDER BY name;",
                (project_id,),
            )
        else:
            cur.execute("SELECT * FROM project_services ORDER BY name;")
        services = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(services), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_services/<id>", methods=["PUT"])
def update_project_service(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE project_services SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Serviço do projeto atualizado com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Serviço do projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_services/<id>", methods=["DELETE"])
def delete_project_service(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM project_services WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Serviço do projeto deletado com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Serviço do projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Documentos do Projeto ---


@app.route("/project_documents", methods=["POST"])
def add_project_document():
    data = request.get_json()
    project_id = data.get("project_id")
    name = data.get("name")
    doc_type = data.get("type")  # 'type' é palavra reservada em Python, usar doc_type
    file_url = data.get("file_url")
    size_kb = data.get("size_kb")
    upload_date = data.get("upload_date")
    uploaded_by = data.get("uploaded_by")
    notes = data.get("notes")

    if not project_id or not name or not file_url:
        return jsonify(
            {"error": "ID do projeto, nome e URL do arquivo são obrigatórios"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Documento do projeto adicionado com sucesso",
                "id": str(document_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_documents", methods=["GET"])
def get_project_documents():
    project_id = request.args.get("project_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if project_id:
            cur.execute(
                "SELECT * FROM project_documents WHERE project_id = %s ORDER BY name;",
                (project_id,),
            )
        else:
            cur.execute("SELECT * FROM project_documents ORDER BY name;")
        documents = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(documents), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_documents/<id>", methods=["PUT"])
def update_project_document(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        # 'type' é palavra reservada, mapear para 'type' do DB se presente
        if key == "doc_type":
            set_clauses.append("type = %s")
        else:
            set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE project_documents SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Documento do projeto atualizado com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Documento do projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_documents/<id>", methods=["DELETE"])
def delete_project_document(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM project_documents WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Documento do projeto deletado com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Documento do projeto não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Versões de Documentos ---


@app.route("/document_versions", methods=["POST"])
def add_document_version():
    data = request.get_json()
    document_id = data.get("document_id")
    version_number = data.get("version_number")
    file_url = data.get("file_url")
    upload_date = data.get("upload_date")
    uploaded_by = data.get("uploaded_by")
    notes = data.get("notes")

    if not document_id or not version_number or not file_url:
        return jsonify(
            {
                "error": "ID do documento, número da versão e URL do arquivo são obrigatórios"
            }
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO document_versions (document_id, version_number, file_url, upload_date, uploaded_by, notes)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (document_id, version_number, file_url, upload_date, uploaded_by, notes),
        )
        version_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Versão do documento adicionado com sucesso",
                "id": str(version_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/document_versions", methods=["GET"])
def get_document_versions():
    document_id = request.args.get("document_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if document_id:
            cur.execute(
                "SELECT * FROM document_versions WHERE document_id = %s ORDER BY version_number DESC;",
                (document_id,),
            )
        else:
            cur.execute("SELECT * FROM document_versions ORDER BY created_at DESC;")
        versions = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(versions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/document_versions/<id>", methods=["PUT"])
def update_document_version(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE document_versions SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Versão do documento atualizada com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Versão do documento não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/document_versions/<id>", methods=["DELETE"])
def delete_document_version(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM document_versions WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Versão do documento deletada com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Versão do documento não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Diários de Obra (RDOs) ---


@app.route("/daily_logs", methods=["POST"])
def add_daily_log():
    data = request.get_json()
    project_id = data.get("project_id")
    log_date = data.get("log_date")
    weather = data.get("weather")
    personnel = data.get("personnel")
    notes = data.get("notes")
    materials_received = data.get("materials_received")
    equipment_used = data.get("equipment_used")
    occurrences = data.get("occurrences")
    location_lat = data.get("location_lat")
    location_lon = data.get("location_lon")

    if not project_id or not log_date:
        return jsonify({"error": "ID do projeto e data do log são obrigatórios"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
        cur.close()
        conn.close()
        return jsonify(
            {"message": "Diário de obra adicionado com sucesso", "id": str(log_id)}
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_logs", methods=["GET"])
def get_daily_logs():
    project_id = request.args.get("project_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if project_id:
            cur.execute(
                "SELECT * FROM daily_logs WHERE project_id = %s ORDER BY log_date DESC;",
                (project_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_logs ORDER BY log_date DESC;")
        logs = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_logs/<id>", methods=["PUT"])
def update_daily_log(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = (
        f"UPDATE daily_logs SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"
    )

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Diário de obra atualizado com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Diário de obra não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_logs/<id>", methods=["DELETE"])
def delete_daily_log(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_logs WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Diário de obra deletado com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Diário de obra não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Atividades do RDO ---


@app.route("/daily_log_activities", methods=["POST"])
def add_daily_log_activity():
    data = request.get_json()
    daily_log_id = data.get("daily_log_id")
    step_name = data.get("step_name")
    activity_type = data.get("activity_type")
    quantity = data.get("quantity")
    unit = data.get("unit")
    observations = data.get("observations")

    if not daily_log_id or not step_name:
        return jsonify(
            {"error": "ID do diário de obra e nome da etapa são obrigatórios"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO daily_log_activities (daily_log_id, step_name, activity_type, quantity, unit, observations)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (daily_log_id, step_name, activity_type, quantity, unit, observations),
        )
        activity_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Atividade do diário de obra adicionada com sucesso",
                "id": str(activity_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_activities", methods=["GET"])
def get_daily_log_activities():
    daily_log_id = request.args.get("daily_log_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if daily_log_id:
            cur.execute(
                "SELECT * FROM daily_log_activities WHERE daily_log_id = %s ORDER BY created_at DESC;",
                (daily_log_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_log_activities ORDER BY created_at DESC;")
        activities = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(activities), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_activities/<id>", methods=["PUT"])
def update_daily_log_activity(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE daily_log_activities SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Atividade do diário de obra atualizada com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Atividade do diário de obra não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_activities/<id>", methods=["DELETE"])
def delete_daily_log_activity(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM daily_log_activities WHERE id = %s RETURNING id;", (id,)
        )
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Atividade do diário de obra deletada com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Atividade do diário de obra não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Custos do RDO ---


@app.route("/daily_log_costs", methods=["POST"])
def add_daily_log_cost():
    data = request.get_json()
    daily_log_id = data.get("daily_log_id")
    description = data.get("description")
    value = data.get("value")
    category = data.get("category")
    associated_step = data.get("associated_step")

    if not daily_log_id or not description or value is None:
        return jsonify(
            {"error": "ID do diário de obra, descrição e valor são obrigatórios"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO daily_log_costs (daily_log_id, description, value, category, associated_step)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (daily_log_id, description, value, category, associated_step),
        )
        cost_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Custo do diário de obra adicionado com sucesso",
                "id": str(cost_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_costs", methods=["GET"])
def get_daily_log_costs():
    daily_log_id = request.args.get("daily_log_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if daily_log_id:
            cur.execute(
                "SELECT * FROM daily_log_costs WHERE daily_log_id = %s ORDER BY created_at DESC;",
                (daily_log_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_log_costs ORDER BY created_at DESC;")
        costs = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(costs), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_costs/<id>", methods=["PUT"])
def update_daily_log_cost(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE daily_log_costs SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Custo do diário de obra atualizado com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Custo do diário de obra não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_costs/<id>", methods=["DELETE"])
def delete_daily_log_cost(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_log_costs WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Custo do diário de obra deletado com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Custo do diário de obra não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Fotos do RDO ---


@app.route("/daily_log_photos", methods=["POST"])
def add_daily_log_photo():
    data = request.get_json()
    daily_log_id = data.get("daily_log_id")
    photo_url = data.get("photo_url")
    description = data.get("description")
    upload_date = data.get("upload_date")
    uploaded_by = data.get("uploaded_by")

    if not daily_log_id or not photo_url:
        return jsonify(
            {"error": "ID do diário de obra e URL da foto são obrigatórios"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO daily_log_photos (daily_log_id, photo_url, description, upload_date, uploaded_by)
               VALUES (%s, %s, %s, %s, %s) RETURNING id;""",
            (daily_log_id, photo_url, description, upload_date, uploaded_by),
        )
        photo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Foto do diário de obra adicionada com sucesso",
                "id": str(photo_id),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_photos", methods=["GET"])
def get_daily_log_photos():
    daily_log_id = request.args.get("daily_log_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if daily_log_id:
            cur.execute(
                "SELECT * FROM daily_log_photos WHERE daily_log_id = %s ORDER BY upload_date DESC;",
                (daily_log_id,),
            )
        else:
            cur.execute("SELECT * FROM daily_log_photos ORDER BY upload_date DESC;")
        photos = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(photos), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_photos/<id>", methods=["PUT"])
def update_daily_log_photo(id):
    data = request.get_json()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    if not set_clauses:
        return jsonify({"error": "Nenhum dado fornecido para atualização"}), 400

    values.append(id)
    query = f"UPDATE daily_log_photos SET {', '.join(set_clauses)} WHERE id = %s RETURNING id;"

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, values)
        updated_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if updated_id:
            return jsonify(
                {
                    "message": "Foto do diário de obra atualizada com sucesso",
                    "id": str(updated_id[0]),
                }
            ), 200
        return jsonify({"error": "Foto do diário de obra não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/daily_log_photos/<id>", methods=["DELETE"])
def delete_daily_log_photo(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM daily_log_photos WHERE id = %s RETURNING id;", (id,))
        deleted_id = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_id:
            return jsonify(
                {
                    "message": "Foto do diário de obra deletada com sucesso",
                    "id": str(deleted_id[0]),
                }
            ), 200
        return jsonify({"error": "Foto do diário de obra não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # --- Rotas para Associação Projeto-Equipe ---


@app.route("/project_team_members", methods=["POST"])
def add_project_team_member():
    data = request.get_json()
    project_id = data.get("project_id")
    team_member_id = data.get("team_member_id")

    if not project_id or not team_member_id:
        return jsonify(
            {"error": "ID do projeto e ID do membro da equipe são obrigatórios"}
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO project_team_members (project_id, team_member_id)
               VALUES (%s, %s) RETURNING project_id, team_member_id;""",
            (project_id, team_member_id),
        )
        # Para chaves primárias compostas, RETURNING retorna ambas as colunas
        assigned_ids = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "message": "Associação projeto-equipe adicionada com sucesso",
                "project_id": str(assigned_ids[0]),
                "team_member_id": str(assigned_ids[1]),
            }
        ), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_team_members", methods=["GET"])
def get_project_team_members():
    project_id = request.args.get("project_id")
    team_member_id = request.args.get("team_member_id")
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
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
        cur.close()
        conn.close()
        return jsonify(associations), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/project_team_members", methods=["DELETE"])
def delete_project_team_member():
    data = request.get_json()
    project_id = data.get("project_id")
    team_member_id = data.get("team_member_id")

    if not project_id or not team_member_id:
        return jsonify(
            {
                "error": "ID do projeto e ID do membro da equipe são obrigatórios para exclusão"
            }
        ), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM project_team_members WHERE project_id = %s AND team_member_id = %s RETURNING project_id, team_member_id;",
            (project_id, team_member_id),
        )
        deleted_ids = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if deleted_ids:
            return jsonify(
                {
                    "message": "Associação projeto-equipe deletada com sucesso",
                    "project_id": str(deleted_ids[0]),
                    "team_member_id": str(deleted_ids[1]),
                }
            ), 200
        return jsonify({"error": "Associação projeto-equipe não encontrada"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
