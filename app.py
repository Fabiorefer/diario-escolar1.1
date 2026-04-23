from flask import Flask, render_template, request, redirect, session, send_file
from pymongo import MongoClient
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "segredo_dev")

# ===============================
# MONGODB
# ===============================
mongo_uri = os.environ.get("MONGO_URI")

if not mongo_uri:
    raise Exception("MONGO_URI não configurada")

client = MongoClient(mongo_uri)
db = client["diario_escolar"]

# ===============================
# LOGIN
# ===============================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        user = db.usuarios.find_one({"usuario": usuario})

        if user and check_password_hash(user["senha"], senha):
            session["usuario"] = usuario
            return redirect("/menu")
        else:
            return render_template("login.html", erro="Usuário ou senha inválidos")

    return render_template("login.html")

# ===============================
# CRIAR USUÁRIO
# ===============================
@app.route("/criar", methods=["GET","POST"])
def criar_usuario():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if db.usuarios.find_one({"usuario": usuario}):
            return "Usuário já existe!"

        senha_hash = generate_password_hash(senha)

        db.usuarios.insert_one({
            "usuario": usuario,
            "senha": senha_hash
        })

        return redirect("/")

    return render_template("criar.html")

# ===============================
# MENU
# ===============================
@app.route("/menu")
def menu():
    if "usuario" not in session:
        return redirect("/")
    return render_template("index.html")

# ===============================
# LOGOUT
# ===============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ===============================
# DISCIPLINAS
# ===============================
@app.route("/disciplinas", methods=["GET","POST"])
def disciplinas():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    if request.method == "POST":
        nova = request.form.get("nova_disciplina")
        if nova:
            db.disciplinas.insert_one({
                "professor": professor,
                "disciplina": nova
            })

    lista = db.disciplinas.find({"professor": professor})
    disciplinas = [d["disciplina"] for d in lista]

    return render_template("disciplinas.html", disciplinas=disciplinas)

# ===============================
# TURMAS
# ===============================
@app.route("/turmas", methods=["GET","POST"])
def turmas():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    if request.method == "POST":
        db.turmas.insert_one({
            "professor": professor,
            "disciplina": request.form.get("disciplina"),
            "turma": request.form.get("turma")
        })

    disciplinas = [d["disciplina"] for d in db.disciplinas.find({"professor": professor})]
    registros = [(t["disciplina"], t["turma"]) for t in db.turmas.find({"professor": professor})]

    return render_template("turmas.html", disciplinas=disciplinas, registros=registros)

# ===============================
# ALUNOS
# ===============================
@app.route("/alunos", methods=["GET","POST"])
def alunos():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    if request.method == "POST":
        db.alunos.insert_one({
            "professor": professor,
            "disciplina": request.form.get("disciplina"),
            "turma": request.form.get("turma"),
            "aluno": request.form.get("aluno")
        })

    disciplinas = [d["disciplina"] for d in db.disciplinas.find({"professor": professor})]
    turmas = list(set([t["turma"] for t in db.turmas.find({"professor": professor})]))
    lista = [(a["disciplina"], a["turma"], a["aluno"]) for a in db.alunos.find({"professor": professor})]

    return render_template("alunos.html", disciplinas=disciplinas, turmas=turmas, alunos=lista)

# ===============================
# RELATÓRIO (TELA)
# ===============================
@app.route("/relatorio")
def relatorio():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplina = request.args.get("disciplina")
    turma = request.args.get("turma")

    disciplinas = list(set([d["disciplina"] for d in db.disciplinas.find({"professor": professor})]))
    turmas = list(set([t["turma"] for t in db.turmas.find({"professor": professor})]))

    alunos = []

    if disciplina and turma:
        alunos = [a["aluno"] for a in db.alunos.find({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma
        })]

    return render_template("relatorio.html",
        disciplinas=disciplinas,
        turmas=turmas,
        alunos=alunos
    )

# ===============================
# RELATÓRIO PDF
# ===============================
@app.route("/relatorio_pdf")
def relatorio_pdf():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplina = request.args.get("disciplina")
    turma = request.args.get("turma")
    bimestre = request.args.get("bimestre")
    aluno_especifico = request.args.get("aluno")

    # ALUNOS
    if aluno_especifico:
        alunos = [aluno_especifico]
    else:
        alunos = [a["aluno"] for a in db.alunos.find({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma
        })]

    # NOTAS
    notas_db = db.notas.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma,
        "bimestre": bimestre
    })

    notas = {n["aluno"]: n for n in notas_db}

    # PDF
    arquivo = "/tmp/relatorio.pdf"
    doc = SimpleDocTemplate(arquivo, pagesize=A4)

    styles = getSampleStyleSheet()
    elementos = []

    titulo = "Relatório Escolar"
    if aluno_especifico:
        titulo += f" - {aluno_especifico}"

    elementos.append(Paragraph(titulo, styles["Title"]))
    elementos.append(Spacer(1,10))
    elementos.append(Paragraph(f"Disciplina: {disciplina}", styles["Normal"]))
    elementos.append(Paragraph(f"Turma: {turma}", styles["Normal"]))
    elementos.append(Paragraph(f"Bimestre: {bimestre}", styles["Normal"]))
    elementos.append(Spacer(1,20))

    dados = [["Aluno","P1","P2","Trab","Part","Tarefa","Média"]]

    for aluno in alunos:
        n = notas.get(aluno, {})
        p1 = n.get("p1",0)
        p2 = n.get("p2",0)
        trab = n.get("trab",0)
        part = n.get("part",0)
        tarefa = n.get("tarefa",0)

        media = round((p1*0.3)+(p2*0.3)+(trab*0.1333)+(part*0.1333)+(tarefa*0.1333),1)

        dados.append([aluno,p1,p2,trab,part,tarefa,media])

    tabela = Table(dados)
    tabela.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black)
    ]))

    elementos.append(tabela)

    doc.build(elementos)

    return send_file(arquivo, as_attachment=True)

# ===============================
# TESTE
# ===============================
@app.route("/teste")
def teste():
    return "API OK 🚀"

application = app
