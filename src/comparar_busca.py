"""Compara o tempo de busca: lista (O(n)) vs. hash (O(1)). Resultado para o artigo."""
import time

from estruturas import buscar_na_lista, montar_hashes, montar_totais
from leitor_csv import ler_todos_anos

REPETICOES = 1000

linhas = ler_todos_anos()
municipios, escolas = montar_hashes(linhas)
totais = montar_totais(escolas)

# Lista com todos os registros, para a busca sem hash
registros = []
for escola in escolas.values():
    registros.extend(escola.registros)

chave = ("CAMPO GRANDE", 2018)

# Busca na lista: percorre todos os registros a cada vez
inicio = time.perf_counter()
for _ in range(REPETICOES):
    na_lista = buscar_na_lista(registros, chave[0], chave[1])
tempo_lista = time.perf_counter() - inicio

# Busca no hash: vai direto na chave
inicio = time.perf_counter()
for _ in range(REPETICOES):
    no_hash = totais[chave]
tempo_hash = time.perf_counter() - inicio

print()
print("Busca:", chave, "| repetições:", REPETICOES, "| registros:", len(registros))
print("Mesmo resultado?", na_lista.aprovados == no_hash.aprovados)
print(f"Lista: {tempo_lista * 1000:.2f} ms no total ({tempo_lista / REPETICOES * 1e6:.1f} µs por busca)")
print(f"Hash:  {tempo_hash * 1000:.4f} ms no total ({tempo_hash / REPETICOES * 1e6:.3f} µs por busca)")
print(f"O hash foi {tempo_lista / tempo_hash:.0f}x mais rápido")
print()
print(f"Campo Grande 2018: aprovação {no_hash.taxa_aprovacao():.1f}% | abandono {no_hash.taxa_abandono():.1f}%")
