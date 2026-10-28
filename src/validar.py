"""Confere o banco (dados/dac.db) contra os CSVs. Rode depois de src/banco.py."""
from collections import Counter

from banco import (conectar, contar_por_ano, contar_sem_base_por_ano,
                   registros_com_matricula_errada, registros_com_soma_errada)
from leitor_csv import ler_todos_anos

conexao = conectar()

# 1. Quantidade por ano: banco vs CSV
no_csv = Counter(int(linha["AnoReferencia"]) for linha in ler_todos_anos())
no_banco = contar_por_ano(conexao)
print("\nAno   CSV   Banco  OK?")
for ano in sorted(no_csv):
    ok = "sim" if no_csv[ano] == no_banco.get(ano) else "NÃO"
    print(ano, f"{no_csv[ano]:5}", f"{no_banco.get(ano, 0):6}", " ", ok)

# 2. Regras de soma (lista vazia = tudo certo)
print("\nSoma das situações != MatriculasTotal:", len(registros_com_soma_errada(conexao)), "registros")
print("Inicial + AposCenso != MatriculasTotal:", len(registros_com_matricula_errada(conexao)), "registros")

# 3. Escolas sem base para calcular taxa (divisão por zero)
print("\nEscolas com aprovados + reprovados + abandono = 0, por ano:")
for ano, quantidade in contar_sem_base_por_ano(conexao).items():
    print(ano, "->", quantidade, "de", no_banco[ano])

conexao.close()
