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
# RELATÓRIO
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
# RELATÓRIO PDF (CORRIGIDO)
# ===============================
@app.route("/relatorio_pdf")
def relatorio_pdf():

    if "usuario" not in session:
        return redirect("/")

    # 🔒 segurança extra (dica profissional)
    if request.method != "GET":
        return redirect("/relatorio")

    professor = session["usuario"]

    disciplina = request.args.get("disciplina")
    turma = request.args.get("turma")
    bimestre = request.args.get("bimestre")
    aluno_filtro = request.args.get("aluno")

    # 🚨 BLOQUEIO (resolve seu problema do PDF automático)
    if not disciplina or not turma or not bimestre:
        return redirect("/relatorio")

    # ===============================
    # ALUNOS
    # ===============================
    alunos = [a["aluno"] for a in db.alunos.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    })]

    # filtro individual
    if aluno_filtro:
        alunos = [aluno_filtro]

    # ===============================
    # NOTAS
    # ===============================
    notas_db = db.notas.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma,
        "bimestre": bimestre
    })

    notas = {n["aluno"]: n for n in notas_db}

    # ===============================
    # PRESENÇA (AGRUPADA)
    # ===============================
    presencas_db = list(db.presenca.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    }))

    datas_presenca = sorted(list(set([p["data"] for p in presencas_db])))

    presencas = {}
    for p in presencas_db:
        presencas.setdefault(p["aluno"], {})[p["data"]] = p["valor"]

    # ===============================
    # CONTEÚDOS
    # ===============================
    conteudos_db = list(db.conteudos.find({
        "professor": professor,
        "disciplina": disciplina,
        "turma": turma
    }).sort("data", 1))

    # ===============================
    # PDF
    # ===============================
    arquivo = "/tmp/relatorio.pdf"
    doc = SimpleDocTemplate(arquivo, pagesize=A4)

    styles = getSampleStyleSheet()
    elementos = []

    # ===============================
    # CABEÇALHO
    # ===============================
    titulo = f"Relatório do Aluno: {aluno_filtro}" if aluno_filtro else "Relatório da Turma"

    elementos.append(Paragraph(titulo, styles["Title"]))
    elementos.append(Spacer(1,10))
    elementos.append(Paragraph(f"Disciplina: {disciplina}", styles["Normal"]))
    elementos.append(Paragraph(f"Turma: {turma}", styles["Normal"]))
    elementos.append(Paragraph(f"Bimestre: {bimestre}", styles["Normal"]))
    elementos.append(Spacer(1,20))

    # ===============================
    # TABELA DE NOTAS
    # ===============================
    elementos.append(Paragraph("Notas", styles["Heading2"]))
    elementos.append(Spacer(1,10))

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

    tabela_notas = Table(dados)
    tabela_notas.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black)
    ]))

    elementos.append(tabela_notas)
    elementos.append(Spacer(1,20))

    # ===============================
    # PRESENÇA
    # ===============================
    elementos.append(Paragraph("Presenças", styles["Heading2"]))
    elementos.append(Spacer(1,10))

    if aluno_filtro:
        # 🔹 PRESENÇA INDIVIDUAL (lista por data)
        for data in datas_presenca:
            valor = presencas.get(aluno_filtro, {}).get(data, "-")
            elementos.append(Paragraph(f"{data}: {valor}", styles["Normal"]))
            elementos.append(Spacer(1,5))
    else:
        # 🔹 PRESENÇA DA TURMA (tabela)
        cabecalho = ["Aluno"] + datas_presenca
        dados_presenca = [cabecalho]

        for aluno in alunos:
            linha = [aluno]
            for data in datas_presenca:
                linha.append(presencas.get(aluno, {}).get(data, "-"))
            dados_presenca.append(linha)

        tabela_presenca = Table(dados_presenca)
        tabela_presenca.setStyle(TableStyle([
            ("GRID",(0,0),(-1,-1),1,colors.black),
            ("BACKGROUND",(0,0),(-1,0),colors.lightgrey)
        ]))

        elementos.append(tabela_presenca)

    elementos.append(Spacer(1,20))

    # ===============================
    # CONTEÚDOS
    # ===============================
    elementos.append(Paragraph("Conteúdos das Aulas", styles["Heading2"]))
    elementos.append(Spacer(1,10))

    for c in conteudos_db:
        elementos.append(Paragraph(f"<b>{c['data']}</b> - {c['conteudo']}", styles["Normal"]))
        elementos.append(Spacer(1,6))

    # ===============================
    # GERAR PDF
    # ===============================
    doc.build(elementos)

    return send_file(arquivo, as_attachment=True)

# ===============================
# VERCEL
# ===============================
application = app
