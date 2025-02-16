import requests
from bs4 import BeautifulSoup
import os
from tqdm import tqdm  # Para barra de progresso
from concurrent.futures import ThreadPoolExecutor, as_completed  # Para download paralelo
import datetime  # Para registrar a data e hora no log
import csv  # Para manipular arquivos CSV
import logging
from logging.handlers import RotatingFileHandler
import configparser
import hashlib

# Configuração do logger
log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log_file = os.path.join(log_folder, "download_log.txt")
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)  # 5 MB por arquivo, 5 backups
logging.basicConfig(level=logging.DEBUG, handlers=[handler], format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar configurações
config = configparser.ConfigParser()
config.read('config.ini')

# Parâmetros de configuração
url_base = config.get('Settings', 'url_base', fallback="https://n8n-temp-uploads.s3.fr-par.scw.cloud/")
max_threads = config.getint('Settings', 'max_threads', fallback=5)

# Cores ANSI
RESET = "\033[0m"
RED = "\033[91m"

# Função para exibir o menu
def exibir_menu():
    print("\n--- MENU ---")
    print("1. Listar todos os arquivos")
    print("2. Baixar todos os arquivos")
    print("3. Baixar arquivos por tipo")
    print("4. Baixar arquivos por nome")
    print("5. Verificar e baixar novos arquivos")
    print("6. Sair")
    return input("Escolha uma opção: ")

# Função para filtrar arquivos por tipo
def filtrar_arquivos_por_tipo(links, tipo):
    """Filtra arquivos por tipo (extensão)."""
    tipo = tipo.lower()  # Converte o tipo para minúsculas
    return [link for link in links if link.lower().endswith(tipo)]  # Converte o link para minúsculas

# Função para filtrar arquivos por nome
def filtrar_arquivos_por_nome(links, nome):
    """Filtra arquivos por nome."""
    nome = nome.lower()  # Converte o nome para minúsculas
    return [link for link in links if nome in link.lower()]  # Converte o link para minúsculas

# Função para criar pastas organizadas por tipo de arquivo
def criar_pasta_por_tipo(download_folder, tipo):
    """Cria uma pasta para armazenar arquivos de um tipo específico."""
    pasta = tipo.replace(".", "")
    caminho_pasta = os.path.join(download_folder, pasta)

    if not os.path.exists(caminho_pasta):
        os.makedirs(caminho_pasta)
    return caminho_pasta

# Função para ajustar o nome do arquivo
def ajustar_nome_arquivo(file_name, excluir_11_caracteres):
    """Ajusta o nome do arquivo, excluindo os 11 primeiros caracteres se necessário."""
    if excluir_11_caracteres and len(file_name) > 11:
        return file_name[11:]  # Exclui os 11 primeiros caracteres
    return file_name

# Função para calcular o checksum MD5 de um arquivo
def calcular_md5(file_path):
    """Calcula o checksum MD5 de um arquivo."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Função para baixar um único arquivo com barra de progresso
def baixar_arquivo(link, download_folder, excluir_11_caracteres, tentativas=3):
    """
    Baixa um arquivo da URL especificada, com suporte a tentativas em caso de falha.

    :param link: URL do arquivo a ser baixado.
    :param download_folder: Pasta onde o arquivo será salvo.
    :param excluir_11_caracteres: Se True, exclui os 11 primeiros caracteres do nome do arquivo.
    :param tentativas: Número de tentativas para baixar o arquivo em caso de falha.
    :return: Dicionário com o status e mensagem do download.
    """
    file_name = link.split('/')[-1]
    file_name_ajustado = ajustar_nome_arquivo(file_name, excluir_11_caracteres)
    tipo = os.path.splitext(file_name_ajustado)[1]  # Obtém a extensão do arquivo (ex: .jpg)
    caminho_pasta = criar_pasta_por_tipo(download_folder, tipo)
    file_path = os.path.join(caminho_pasta, file_name_ajustado)

    for tentativa in range(tentativas):
        try:
            response = requests.get(link, stream=True)
            response.raise_for_status()  # Verifica se a requisição foi bem-sucedida

            # Obtém o tamanho total do arquivo em bytes
            total_size = int(response.headers.get('content-length', 0))

            # Cria uma barra de progresso para o arquivo atual
            with tqdm(
                total=total_size, unit='B', unit_scale=True, desc=file_name_ajustado, ncols=100
            ) as pbar:
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                        pbar.update(len(chunk))  # Atualiza a barra de progresso

            # Verificação de integridade
            if calcular_md5(file_path) == response.headers.get('ETag', '').strip('"'):
                return {"status": "sucesso", "mensagem": f"{file_name_ajustado} baixado com sucesso na pasta {caminho_pasta}!"}
            else:
                logging.error(f"Checksum falhou para {file_name_ajustado}. O arquivo pode estar corrompido.")
                return {"status": "erro", "mensagem": f"Erro ao baixar {file_name_ajustado}: checksum falhou."}

        except Exception as e:
            logging.error(f"Erro ao baixar {file_name_ajustado} (tentativa {tentativa + 1}): {e}")
            if tentativa == tentativas - 1:
                return {"status": "erro", "mensagem": f"Erro ao baixar {file_name_ajustado}: {e}"}

# Função para baixar arquivos em paralelo
def baixar_arquivos_paralelo(links, download_folder, excluir_11_caracteres, max_threads=5):
    """
    Baixa arquivos em paralelo usando múltiplas threads.

    :param links: Lista de links para os arquivos a serem baixados.
    :param download_folder: Pasta onde os arquivos serão salvos.
    :param excluir_11_caracteres: Se True, exclui os 11 primeiros caracteres do nome dos arquivos.
    :param max_threads: Número máximo de threads a serem usadas para o download.
    """
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    # Listas para armazenar resultados
    arquivos_baixados = []
    erros = []

    # Usando ThreadPoolExecutor para gerenciar as threads
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        # Cria uma lista de futures (tarefas agendadas)
        futures = [
            executor.submit(baixar_arquivo, link, download_folder, excluir_11_caracteres)
            for link in links
        ]

        # Inicializa a barra de progresso geral com cor
        with tqdm(total=len(links), desc=f"{RED}Progresso Total{RESET}", unit="arquivo") as pbar:
            # Aguarda a conclusão de cada future e exibe o resultado
            for future in as_completed(futures):
                resultado = future.result()
                print(resultado["mensagem"])

                # Atualiza a barra de progresso geral
                pbar.update(1)

                # Classifica o resultado
                if resultado["status"] == "sucesso":
                    arquivos_baixados.append(resultado["mensagem"])
                elif resultado["status"] == "erro":
                    erros.append(resultado["mensagem"])

    # Mensagem personalizada de conclusão
    mensagem_conclusao = (
        f"\nTodos os downloads foram concluídos!\n"
        f"Total de arquivos baixados: {len(arquivos_baixados)}.\n"
        f"Total de erros: {len(erros)}."
    )
    print(mensagem_conclusao)

    # Log de conclusão
    registrar_log(mensagem_conclusao, arquivos_baixados, erros)

# Função para registrar log de conclusão
def registrar_log(mensagem_conclusao, arquivos_baixados, erros):
    """
    Registra as informações de conclusão no arquivo de log.

    :param mensagem_conclusao: Mensagem de conclusão dos downloads.
    :param arquivos_baixados: Lista de arquivos que foram baixados com sucesso.
    :param erros: Lista de erros ocorridos durante o download.
    """
    logging.info(mensagem_conclusao)
    logging.info("=== Arquivos Baixados ===")
    for arquivo in arquivos_baixados:
        logging.info(arquivo)

    logging.info("\n=== Erros ===")
    for erro in erros:
        logging.error(erro)

# Função para salvar os links em um arquivo CSV
def salvar_links_csv(links, arquivo_csv):
    """Salva os links em um arquivo CSV, evitando duplicatas."""
    links_existentes = set(carregar_links_csv(arquivo_csv))  # Carrega links existentes em um set

    arquivo_existe = os.path.exists(arquivo_csv)

    with open(arquivo_csv, mode='a', newline='') as file:
        writer = csv.writer(file)

        if not arquivo_existe:
            writer.writerow(["Link", "Nome do Arquivo", "Data de Download", "Status"])

        data_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for link in links:
            if link not in links_existentes:  # Verifica se o link já existe
                file_name = link.split('/')[-1]
                writer.writerow([link, file_name, data_hora, "Baixado"])
                links_existentes.add(link)  # Adiciona o link ao conjunto para evitar futuras duplicatas

# Função para carregar os links de um arquivo CSV
def carregar_links_csv(arquivo_csv):
    """Carrega os links de um arquivo CSV."""
    if not os.path.exists(arquivo_csv):
        return []  # Retorna uma lista vazia se o arquivo não existir

    links = []
    with open(arquivo_csv, mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Pula o cabeçalho
        for row in reader:
            links.append(row[0])  # Adiciona o link (primeira coluna)
    return links

# Função para verificar e baixar novos arquivos
def verificar_e_baixar_novos_arquivos(links, download_folder, arquivo_csv):
    """Verifica se há novos arquivos e os baixa se o usuário confirmar."""
    links_baixados = carregar_links_csv(arquivo_csv)

    novos_links = [link for link in links if link not in links_baixados]

    if not novos_links:
        print("\nNenhum novo arquivo encontrado.")
        return

    print("\nNovos arquivos encontrados:")
    for link in novos_links:
        print(link)

    confirmacao = input("\nDeseja baixar os novos arquivos? (s/n): ")
    if confirmacao.lower() == "s":
        excluir_11_caracteres = input("Deseja excluir os 11 primeiros caracteres do nome do arquivo? (s/n): ").lower() == "s"
        baixar_arquivos_paralelo(novos_links, download_folder, excluir_11_caracteres, max_threads)

        salvar_links_csv(novos_links, arquivo_csv)

# Função principal
def main():
    """Função principal que executa o script."""
    download_folder = "downloads"
    arquivo_csv = "links_baixados.csv"

    # Fazendo a requisição para obter o conteúdo do XML
    try:
        response = requests.get(url_base)
        response.raise_for_status()  # Verifica se a requisição foi bem-sucedida
        xml_content = response.content
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return  # Encerra a função se a requisição falhar

    # Parseando o XML
    soup = BeautifulSoup(xml_content, 'xml')

    # Encontrando todas as tags <Key>
    keys = soup.find_all('Key')

    # Gerando os links completos
    links = [f"{url_base}{key.get_text()}" for key in keys]

    while True:
        opcao = exibir_menu()

        if opcao == "1":  # Listar todos os arquivos
            print("\nArquivos disponíveis:")
            for link in links:
                print(link)

        elif opcao == "2":  # Baixar todos os arquivos
            excluir_11_caracteres = input("\nDeseja excluir os 11 primeiros caracteres do nome do arquivo? (s/n): ").lower() == "s"
            print("\nIniciando o download de todos os arquivos...")
            baixar_arquivos_paralelo(links, download_folder, excluir_11_caracteres, max_threads)
            salvar_links_csv(links, arquivo_csv)  # Salva os links no CSV
            print("Todos os arquivos foram baixados e os links salvos no CSV.")

        elif opcao == "3":  # Baixar arquivos por tipo
            tipo = input("\nDigite o tipo de arquivo que deseja baixar (ex: .jpg, .zip): ")
            links_filtrados = filtrar_arquivos_por_tipo(links, tipo)

            quantidade = len(links_filtrados)
            print(f"\nForam encontrados {quantidade} arquivos do tipo {tipo}.")

            if not links_filtrados:
                print(f"Nenhum arquivo do tipo {tipo} encontrado.")
            else:
                print("\nArquivos encontrados:")
                for link in links_filtrados:
                    print(link)
                confirmacao = input("\nDeseja baixar esses arquivos? (s/n): ")
                if confirmacao.lower() == "s":
                    excluir_11_caracteres = input("Deseja excluir os 11 primeiros caracteres do nome do arquivo? (s/n): ").lower() == "s"
                    print("\nIniciando o download dos arquivos filtrados...")
                    baixar_arquivos_paralelo(links_filtrados, download_folder, excluir_11_caracteres, max_threads)
                    salvar_links_csv(links_filtrados, arquivo_csv)  # Salva os links no CSV
                    print("Os arquivos filtrados foram baixados e os links salvos no CSV.")

        elif opcao == "4":  # Baixar arquivos por nome
            nome = input("\nDigite parte do nome do arquivo que deseja baixar: ")
            links_filtrados = filtrar_arquivos_por_nome(links, nome)

            quantidade = len(links_filtrados)
            print(f"\nForam encontrados {quantidade} arquivos com o nome contendo '{nome}'.")

            if not links_filtrados:
                print(f"Nenhum arquivo com o nome contendo '{nome}' encontrado.")
            else:
                print("\nArquivos encontrados:")
                for link in links_filtrados:
                    print(link)
                confirmacao = input("\nDeseja baixar esses arquivos? (s/n): ")
                if confirmacao.lower() == "s":
                    excluir_11_caracteres = input("Deseja excluir os 11 primeiros caracteres do nome do arquivo? (s/n): ").lower() == "s"
                    print("\nIniciando o download dos arquivos filtrados por nome...")
                    baixar_arquivos_paralelo(links_filtrados, download_folder, excluir_11_caracteres, max_threads)
                    salvar_links_csv(links_filtrados, arquivo_csv)  # Salva os links no CSV
                    print("Os arquivos filtrados por nome foram baixados e os links salvos no CSV.")

        elif opcao == "5":  # Verificar e baixar novos arquivos
            verificar_e_baixar_novos_arquivos(links, download_folder, arquivo_csv)

        elif opcao == "6":  # Sair
            print("Saindo...")
            break

        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    main()