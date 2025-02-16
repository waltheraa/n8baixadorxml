## 📋 Descrição

Script Python para download automático de arquivos com organização inteligente por tipo, suporte a download paralelo e sistema de logs. Ideal para baixar e organizar grandes quantidades de arquivos de forma eficiente.

## ✨ Funcionalidades

- 📂 **Organização Automática**: Cria pastas por tipo de arquivo
- 🚀 **Download Paralelo**: Utiliza múltiplas threads para downloads mais rápidos
- 🔍 **Filtragem Inteligente**: Filtro por tipo de arquivo ou nome
- 📊 **Barra de Progresso**: Acompanhamento visual do progresso
- 📝 **Sistema de Logs**: Registro detalhado de todas as operações
- ✅ **Verificação de Integridade**: Checksum MD5 dos arquivos
- 🔄 **Controle de Duplicatas**: Evita baixar arquivos repetidos
- 📈 **Histórico em CSV**: Mantém registro dos downloads realizados

## 🛠️ Requisitos

- Python 3.x
- Bibliotecas Python:
  ```
  requests>=2.31.0
  beautifulsoup4>=4.12.2
  tqdm>=4.65.0
  ```

## ⚙️ Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/download-manager-n8n.git
cd download-manager-n8n
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure o arquivo `config.ini`:
```ini
[Settings]
url_base = https://n8n-temp-uploads.s3.fr-par.scw.cloud/
max_threads = 5
```

## 🚀 Uso

Execute o script:
```bash
python download_links.py
```

### Menu de Opções

1. **Listar Arquivos**: Mostra todos os arquivos disponíveis
2. **Baixar Todos**: Faz download de todos os arquivos
3. **Baixar por Tipo**: Filtra e baixa por extensão (.jpg, .pdf, etc.)
4. **Baixar por Nome**: Filtra e baixa por parte do nome
5. **Verificar Novos**: Verifica e baixa apenas arquivos novos
6. **Sair**: Encerra o programa

### 💡 Exemplos

Baixar todos os arquivos PDF:
```bash
Escolha uma opção: 3
Digite o tipo de arquivo que deseja baixar: .pdf
```

Baixar arquivos com "relatório" no nome:
```bash
Escolha uma opção: 4
Digite parte do nome do arquivo: relatório
```

## 📁 Estrutura de Pastas

```
.
├── downloads/          # Pasta principal de downloads
│   ├── pdf/           # Arquivos PDF
│   ├── jpg/           # Imagens JPG
│   └── ...           # Outras extensões
├── logs/              # Registros de operações
├── config.ini         # Configurações
├── requirements.txt   # Dependências
└── download_links.py  # Script principal
```

## 📊 Logs e Monitoramento

- Logs salvos em: `logs/download_log.txt`
- Histórico de downloads: `links_baixados.csv`
- Rotação automática de logs (máximo 5MB por arquivo)

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um Fork
2. Criar uma Branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push (`git push origin feature/nova-funcionalidade`)
5. Abrir um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
