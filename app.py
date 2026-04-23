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
# PRESENÇA
# ===============================
@app.route("/presenca", methods=["GET","POST"])
def presenca():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplina = request.values.get("disciplina")
    turma = request.values.get("turma")
    data = request.values.get("data")

    disciplinas = list(set([d["disciplina"] for d in db.disciplinas.find({"professor": professor})]))
    turmas = list(set([t["turma"] for t in db.turmas.find({"professor": professor})]))

    alunos = []
    if disciplina and turma:
        alunos = [a["aluno"] for a in db.alunos.find({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma
        })]

    if request.method == "POST":

        db.presenca.delete_many({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma,
            "data": data
        })

        for i, aluno in enumerate(alunos, start=1):
            valor = request.form.get(f"presenca_{i}") or "F"

            db.presenca.insert_one({
                "professor": professor,
                "disciplina": disciplina,
                "turma": turma,
                "data": data,
                "aluno": aluno,
                "valor": valor
            })

    presencas = {}
    registros = db.presenca.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma,
        "data": data
    })

    for r in registros:
        presencas[r["aluno"]] = r["valor"]

    return render_template("presenca.html",
        disciplinas=disciplinas,
        turmas=turmas,
        disciplina=disciplina,
        turma=turma,
        data=data,
        alunos=alunos,
        presencas=presencas,
        salvo=(request.method=="POST")
    )

# ===============================
# NOTAS
# ===============================
@app.route("/notas", methods=["GET","POST"])
def notas():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplina = request.values.get("disciplina")
    turma = request.values.get("turma")
    bimestre = request.values.get("bimestre")

    disciplinas = list(set([d["disciplina"] for d in db.disciplinas.find({"professor": professor})]))
    turmas = list(set([t["turma"] for t in db.turmas.find({"professor": professor})]))

    alunos = []
    if disciplina and turma:
        alunos = [a["aluno"] for a in db.alunos.find({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma
        })]

    if request.method == "POST":

        db.notas.delete_many({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma,
            "bimestre": bimestre
        })

        for i, aluno in enumerate(alunos, start=1):

            db.notas.insert_one({
                "professor": professor,
                "disciplina": disciplina,
                "turma": turma,
                "bimestre": bimestre,
                "aluno": aluno,
                "p1": float(request.form.get(f"p1_{i}") or 0),
                "p2": float(request.form.get(f"p2_{i}") or 0),
                "trab": float(request.form.get(f"trab_{i}") or 0),
                "part": float(request.form.get(f"part_{i}") or 0),
                "tarefa": float(request.form.get(f"tarefa_{i}") or 0)
            })

    notas = {}
    for r in db.notas.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma,
        "bimestre": bimestre
    }):
        notas[r["aluno"]] = r

    return render_template("notas.html",
        disciplinas=disciplinas,
        turmas=turmas,
        disciplina=disciplina,
        turma=turma,
        bimestre=bimestre,
        alunos=alunos,
        notas=notas,
        salvo=(request.method=="POST")
    )

# ===============================
# CONTEÚDOS
# ===============================
@app.route("/conteudos", methods=["GET","POST"])
def conteudos():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplina = request.values.get("disciplina")
    turma = request.values.get("turma")
    data = request.values.get("data")

    disciplinas = list(set([d["disciplina"] for d in db.disciplinas.find({"professor": professor})]))
    turmas = list(set([t["turma"] for t in db.turmas.find({"professor": professor})]))

    if request.method == "POST":
        conteudo = request.form.get("conteudo")

        db.conteudos.delete_many({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma,
            "data": data
        })

        db.conteudos.insert_one({
            "professor": professor,
            "disciplina": disciplina,
            "turma": turma,
            "data": data,
            "conteudo": conteudo
        })

    atual = db.conteudos.find_one({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma,
        "data": data
    })

    conteudo_atual = atual["conteudo"] if atual else ""

    lista = list(db.conteudos.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    }).sort("data", -1))

    return render_template("conteudos.html",
        disciplinas=disciplinas,
        turmas=turmas,
        disciplina=disciplina,
        turma=turma,
        data=data,
        conteudo_atual=conteudo_atual,
        conteudos=lista,
        salvo=(request.method=="POST")
    )

# ===============================
# RELATÓRIO (TELA)
# ===============================
@app.route("/relatorio")
def relatorio():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplinas = list(set([d["disciplina"] for d in db.disciplinas.find({"professor": professor})]))
    turmas = list(set([t["turma"] for t in db.turmas.find({"professor": professor})]))

    alunos = []
    disciplina = request.args.get("disciplina")
    turma = request.args.get("turma")

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
# RELATÓRIO PDF (GERAL + INDIVIDUAL)
# ===============================
@app.route("/relatorio_pdf")
def relatorio_pdf():

    if "usuario" not in session:
        return redirect("/")

    professor = session["usuario"]

    disciplina = request.args.get("disciplina")
    turma = request.args.get("turma")
    bimestre = request.args.get("bimestre")
    aluno_filtro = request.args.get("aluno")

    alunos = [a["aluno"] for a in db.alunos.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    })]

    if aluno_filtro:
        alunos = [aluno_filtro]

    notas_db = db.notas.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma,
        "bimestre": bimestre
    })

    notas = {n["aluno"]: n for n in notas_db}

    presencas_db = list(db.presenca.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    }))

    datas_presenca = sorted(list(set([p["data"] for p in presencas_db])))

    presencas = {}
    for p in presencas_db:
        presencas.setdefault(p["aluno"], {})[p["data"]] = p["valor"]

    conteudos_db = list(db.conteudos.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    }).sort("data", 1))

    arquivo = "/tmp/relatorio.pdf"
    doc = SimpleDocTemplate(arquivo, pagesize=A4)

    styles = getSampleStyleSheet()
    elementos = []

    titulo = f"Relatório - {aluno_filtro}" if aluno_filtro else "Relatório Escolar"

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
        ("GRID",(0,0),(-1,-1),1,colors.black)
    ]))

    elementos.append(tabela)

    doc.build(elementos)

    return send_file(arquivo, as_attachment=True)

application = app
