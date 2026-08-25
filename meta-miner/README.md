# Meta Ads Miner

Ferramenta local para encontrar páginas/anunciantes na Meta Ads Library que possuem muitos anúncios ativos.

## O que ela faz

1. Você digita uma palavra-chave.
2. O programa busca anúncios ativos relacionados a essa palavra.
3. Descobre as páginas únicas usando o `Page ID`.
4. Consulta cada página individualmente.
5. Conta anúncios únicos retornados pela busca `ACTIVE`.
6. Mostra apenas páginas que atingem o mínimo escolhido.
7. Exibe nome da página, Page ID, quantidade encontrada e links para Facebook e Meta Ad Library.

## Instalação no Windows

Abra o PowerShell dentro da pasta do projeto.

```powershell
python -m pip install -r requirements.txt
```

## Rodar

```powershell
python -m streamlit run app.py
```

O navegador deve abrir sozinho. Se não abrir, copie o endereço mostrado no terminal, normalmente:

```text
http://localhost:8501
```

## Primeiro teste recomendado

Comece pequeno:

- palavra-chave: `marketing digital`
- anúncios para descoberta: `20`
- mínimo de anúncios ativos: `2`
- teto de segurança: `100`

Depois aumente aos poucos.

## O que significa "anúncios ativos encontrados"

O número não é inventado nem é a quantidade de vezes que a página apareceu na busca inicial.

A ferramenta faz uma consulta separada pelo `Page ID` e conta anúncios únicos retornados pela pesquisa `ACTIVE` até o fim da paginação.

Se a coleta atingir o `teto de segurança`, a interface mostra o valor como limitado. Nesse caso, leia como **pelo menos esse número**, não como total exato.

## Cache

Os resultados de páginas ficam em cache SQLite por 12 horas para evitar consultas repetidas. Na interface você pode marcar `Revalidar páginas ignorando cache` para forçar uma nova consulta.

## Arquivos e pastas

- `app.py` — interface Streamlit
- `miner.py` — motor de mineração
- `models.py` — estruturas dos resultados
- `database.py` — cache SQLite
- `utils.py` — utilitários e construção dos links
- `results/` — CSV/JSON salvos automaticamente
- `logs/errors.log` — erros registrados
- `data/cache.sqlite` — cache local

## Scripts de diagnóstico

Os arquivos `_debug_probe.py` e `_debug_graphql.py` foram mantidos para testes técnicos do collector.

## Observação

A ferramenta depende do funcionamento da Meta Ads Library e da biblioteca `meta-ads-collector`. Mudanças na Meta podem exigir atualização do pacote ou do código.
