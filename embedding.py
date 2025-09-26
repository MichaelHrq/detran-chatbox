import os
import openai
import json
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from tqdm import tqdm


# Load environment variables from .env
load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

# Fetch variables
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Connect to the database
connection = None
cursor = None

try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("Connection successful!")
        
    cursor = connection.cursor()

    print("Limpando a tabela 'tb_embedding'...")
    cursor.execute("TRUNCATE TABLE tb_embedding RESTART IDENTITY;")
    print("Tabela limpa com sucesso.")

    with open('detran_servicos.json', 'r', encoding='utf-8') as f:
        produtos = json.load(f)
        
    valores = []
    print("Gerando embeddings para os serviços...")
    for p in tqdm(produtos, desc="Processando servicos"):
        try:
            texto = f"{p['title']} - {p['content']}".strip()
            if not texto:
                continue

            embedding = openai.embeddings.create(
                model="text-embedding-3-small",
                input=texto
            ).data[0].embedding

            valores.append((p['title'], p['url'], p['content'], embedding))
        except Exception as e:
            print(f"Erro ao processar o servico '{p.get('title', 'N/A')}': {e}")
            continue

    if valores:
        print(f"\nInserindo {len(valores)} registros no banco de dados...")
        sql = "INSERT INTO tb_embedding (title, url, content, embedding) VALUES %s"
        execute_values(cursor, sql, valores)
        connection.commit()
        print(f"{len(valores)} registros inseridos com sucesso.")
    else:
        print("⚠️ Nenhum dado válido para inserir.")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
finally:
    if cursor:
        cursor.close()
    if connection:
        connection.close()
        print("Connection closed.")
