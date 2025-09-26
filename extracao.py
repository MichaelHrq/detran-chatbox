import requests
from bs4 import BeautifulSoup
import time
import json

# URL base do site
url_base = "https://www.detran.am.gov.br"

# Lista para armazenar os dados finais de todos os serviços
dados_completos = []

def extrair_links_servicos(url):
    """
    Funcao para extrair os títulos e links de UMA PÁGINA de serviços.
    """
    links_servicos = []
    try:
        print(f"Acessando a pagina de listagem: {url}")
        response = requests.get(url, timeout=15) # Aumentei o timeout para garantir
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        wrapper_div = soup.find("div", class_="wrapper col-12 col-lg-9")

        if wrapper_div:
            articles = wrapper_div.find_all("article", class_="tease-servicos")
            if not articles:
                print("  -> Nenhuma vaga encontrada nesta pagina.")
                return [] # Retorna lista vazia se não houver artigos
                
            for article in articles:
                link_tag = article.find("h2").find("a")
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    link_url = link_tag.get("href")
                    links_servicos.append({"title": title, "url": link_url})
        return links_servicos
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a pagina de listagem {url}: {e}")
        return []

def extrair_conteudo_artigo(url):
    """
    Função para acessar a URL de um serviço e extrair o texto do article-body.
    """
    try:
        print(f"  -> Extraindo conteudo de: {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        article_body = soup.find("div", class_="article-body")

        if article_body:
            # Encontra e remove a div com os botões para não extrair seu texto
            div_botoes = article_body.find("div", class_="row mb-4")
            if div_botoes:
                div_botoes.decompose()
            a_botao = article_body.find("a", class_="btn btn-warning btn-lg float-right")
            text = ''
            if a_botao:
                a_botao.decompose()
                text = ' Link para iniciar o processo: https://digital.detran.am.gov.br/'
            div_footer = article_body.find("div", class_="mb-3 text-right")
            if div_footer:
                div_footer.decompose()

            conteudo_texto = article_body.get_text(separator='\n', strip=True)
            return conteudo_texto + text
            
    except requests.exceptions.RequestException as e:
        print(f"  -> Erro ao extrair o artigo {url}: {e}")
    return None

# --- LÓGICA PRINCIPAL ---

# 1. Loop para percorrer todas as páginas de 1 a 16
todas_as_urls_de_servicos = []
for numero_pagina in range(1, 2): # range(1, 17) vai de 1 a 16
    url_pagina_atual = f"{url_base}/servicos/page/{numero_pagina}/"
    links_da_pagina = extrair_links_servicos(url_pagina_atual)
    todas_as_urls_de_servicos.extend(links_da_pagina)
    time.sleep(1) # Pausa de 1 segundo entre as páginas

# 2. Iterar sobre a lista total de serviços para extrair o conteúdo
if todas_as_urls_de_servicos:
    total_servicos = len(todas_as_urls_de_servicos)
    print(f"\nExtracao de links concluida. Total de {total_servicos} servicos encontrados.")
    print("Iniciando a extracao do conteudo de cada artigo...\n")
    
    for i, servico in enumerate(todas_as_urls_de_servicos):
        print(f"Processando servico {i+1} de {total_servicos}...")
        conteudo = extrair_conteudo_artigo(servico['url'])
        
        if conteudo:
            # Substitui todas as quebras de linha por um espaço
            dados_completos.append({
                "title": servico['title'],
                "url": servico['url'],
                "content": conteudo.replace('\n', ' ')
            })
        time.sleep(1) # Pausa de 1 segundo entre cada artigo

# 3. Imprimir (ou salvar) o resultado final
print("\n--- EXTRACAO FINALIZADA ---")
print(f"Total de {len(dados_completos)} artigos processados com sucesso.\n")

# Exemplo de como acessar o primeiro item da lista:
# if dados_completos:
#     print("--- Exemplo do primeiro resultado ---")
#     print(f"Título: {dados_completos[0]['title']}")
#     print(f"URL: {dados_completos[0]['url']}")
#     print("Conteúdo:")
#     print(dados_completos[0]['content'])

# 4. Salvar os dados em um arquivo JSON
if dados_completos:
    print("Salvando os dados em 'detran_servicos.json'...")
    with open("detran_servicos.json", "w", encoding="utf-8") as f:
        json.dump(dados_completos, f, ensure_ascii=False, indent=4)
    print("Dados salvos com sucesso em 'detran_servicos.json'.")
