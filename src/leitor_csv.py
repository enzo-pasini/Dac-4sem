import csv
import os


def ler_csv(caminho):
    """Lê um CSV e devolve uma lista de dicionários (um por linha/escola)."""
    linhas = []
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        # DictReader usa a primeira linha (cabeçalho) como chaves
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            linhas.append(linha)
    return linhas


def ler_todos_anos(pasta="dados/csv"):
    """Lê todos os CSVs da pasta, um por um, e junta as linhas numa lista só."""
    todas_linhas = []
    for nome_arquivo in sorted(os.listdir(pasta)):
        if nome_arquivo.endswith(".csv"):
            caminho = os.path.join(pasta, nome_arquivo)
            linhas = ler_csv(caminho)
            print(nome_arquivo, "->", len(linhas), "linhas")
            todas_linhas.extend(linhas)
    return todas_linhas


if __name__ == "__main__":
    from normalizacao import normalizar

    linhas = ler_todos_anos()
    print("Total de linhas (todos os anos):", len(linhas))

    # Quantos municípios existem antes e depois de normalizar
    originais = set(linha["NomeMunicipio"] for linha in linhas)
    normalizados = set(normalizar(linha["NomeMunicipio"]) for linha in linhas)
    print("Municípios (nome original):", len(originais))
    print("Municípios (nome normalizado):", len(normalizados))
