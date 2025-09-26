import os
import openai
import psycopg2
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

SUPABASE_CONFIG = {
    "dbname": os.getenv('dbname'),
    "user": os.getenv('user'),
    "password": os.getenv('password'),
    "host": os.getenv('host'),
    "port": os.getenv('port')
}

app = Flask(__name__)
CORS(app)  # libera CORS para todas as origens (uso geral)

def gerar_embedding(texto):
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=texto
    )
    return response.data[0].embedding

def buscar_produtos(embedding, limite=5):
    conn = psycopg2.connect(**SUPABASE_CONFIG)
    cursor = conn.cursor()

    # Converter vetor Python para texto tipo vector
    embedding_sql = str(embedding).replace('\n', '')  # Gera: "[0.1, -0.2, ...]"
    
    sql = f"""
    SELECT title, url, content
    FROM tb_embedding
    ORDER BY embedding <-> '{embedding_sql}'::vector
    LIMIT %s;
    """

    cursor.execute(sql, (limite,))
    resultados = cursor.fetchall()

    cursor.close()
    conn.close()

    produtos = []
    for r in resultados:
        produtos.append({
            "title": r[0],
            "url": r[1],
            "content": r[2]
        })
    return produtos

def gerar_resposta(intencao, produtos):
    # Dicionário com os textos do prompt em cada idioma
    textos = {
            'instrucao_sistema': "Você é um assistente virtual amigável para um departamento de transito. Responda sempre em português do Brasil com um tom empático e prestativo.",
            'header_produtos': "Aqui estão os serviços para usar na sua resposta:"
        }

    # Formata a lista de produtos
    lista_produtos = "\n".join([
        f"- {p['title']}: {p['content']} (Link: {p['url']})"
        for p in produtos
    ])

    # Monta o prompt para o modelo
    prompt_usuario = f"""
A intenção do cliente é: "{intencao}"

{textos['header_produtos']}
{lista_produtos}
"""

    # Chama a API do OpenAI com as novas instruções
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            # Instrução geral sobre como o modelo deve se comportar
            {"role": "system", "content": textos['instrucao_sistema']},
            # A pergunta específica do usuário
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.8
    )

    return response.choices[0].message.content.strip()
        
@app.route("/", methods=["GET"])
def home():
    return "API online"
        
@app.route("/chatbox", methods=["POST"])
def chat_sugestoes():
    data = request.get_json()
    pergunta = data.get("mensagem", "").strip()

    if not pergunta:
        return jsonify({"erro": "Mensagem vazia"}), 400

    try:
        embedding = gerar_embedding(pergunta)
        produtos = buscar_produtos(embedding, limite=5)
        if not produtos:
            return jsonify({"resposta": "Não consegui encontrar nenhum serviço adequado, desculpe!"})
        resposta = gerar_resposta(pergunta, produtos)
        return jsonify({"resposta": resposta})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("flask_port", 5000))
    app.run(host="0.0.0.0", port=port)