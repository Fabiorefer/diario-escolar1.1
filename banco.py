import os
from pymongo import MongoClient

def conectar():
    mongo_uri = os.environ.get("MONGO_URI")

    if not mongo_uri:
        raise Exception("MONGO_URI não configurada")

    client = MongoClient(mongo_uri)
    db = client["diario_escolar"]
    return db


def criar_banco():
    db = conectar()

    db["professores"]
    db["alunos"]
    db["conteudos"]
    db["presenca"]
    db["notas"]

    print("Banco MongoDB conectado com sucesso")
