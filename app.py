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


def buscar_produtos(embedding, limite=1):
    conn = psycopg2.connect(**SUPABASE_CONFIG)
    cursor = conn.cursor()

    # Converter vetor Python para texto tipo vector
    embedding_sql = str(embedding).replace(
        '\n', '')  # Gera: "[0.1, -0.2, ...]"

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
    # textos = {
    #         'instrucao_sistema': "Você é um assistente virtual amigável para um departamento de transito. Responda sempre em português do Brasil com um tom empático e prestativo.",
    #         'header_produtos': "Aqui estão os serviços para usar na sua resposta:"
    #     }
    textos = {
        "instrucao_sistema": (
            "Você é um assistente virtual amigável e prestativo que responde perguntas sobre serviços públicos "
            "do estado do Amazonas. Você tem acesso a informações sobre dois órgãos principais:\n\n"
            "1. **DETRAN-AM** (Departamento Estadual de Trânsito do Amazonas): responsável por serviços de "
            "transporte, veículos, habilitação, infrações e documentação veicular.\n"
            "2. **Defensoria Pública do Estado do Amazonas (DPE-AM)**: responsável por prestar assistência jurídica "
            "gratuita, orientações legais, atendimento a pessoas em situação de vulnerabilidade e defesa de direitos civis.\n\n"
            "Seu papel é entender a intenção do usuário, identificar a qual órgão o serviço está relacionado "
            "(DETRAN-AM ou DPE-AM) e responder de forma clara, empática e útil, sempre em português do Brasil.\n\n"
            "Se o serviço estiver relacionado à **Defensoria Pública**, inclua no final da resposta o seguinte texto, "
            "sem alterações e no mesmo formato de link Markdown:\n\n"
            "Agende um novo atendimento, inicie seus atendimentos agendados e visualize informações sobre seus agendamentos "
            "[clicando aqui](https://atendimento.defensoria.am.def.br/)\n\n"
            "Caso o assunto não esteja diretamente relacionado a nenhum desses órgãos, responda gentilmente que "
            "seu foco atual é fornecer informações sobre serviços do DETRAN-AM e da DPE-AM, e oriente o usuário "
            "a procurar o canal oficial correspondente. e avise que em breve estarei apto a ajudar com outros serviços."
        ),
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
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": textos['instrucao_sistema']},
            {"role": "user", "content": prompt_usuario}
        ],
        temperature=0.8
    )

    return response.choices[0].message.content.strip(), prompt_usuario


def gerar_log(pergunta, resposta):
    try:
        conn = psycopg2.connect(**SUPABASE_CONFIG)
        cursor = conn.cursor()
        sql = """
        INSERT INTO logs (pergunta, resposta)
        VALUES (%s, %s);
        """
        cursor.execute(sql, (pergunta, resposta))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Erro ao inserir no banco:", e)


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
        produtos = buscar_produtos(embedding, limite=1)
        if not produtos:
            return jsonify({"resposta": "Não consegui encontrar nenhum serviço adequado, desculpe!"})
        resposta, prompt = gerar_resposta(pergunta, produtos)
        gerar_log(pergunta, resposta)
        return jsonify({"resposta": resposta, "prompt": prompt})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


if __name__ == "__main__":
    # port = int(os.environ.get("flask_port", 5000))
    app.run(host="0.0.0.0", port=5000)
