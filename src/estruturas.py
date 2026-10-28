from modelos import Municipio, Escola, criar_registro
from normalizacao import normalizar


class Totais:
    """Soma dos números de várias escolas (ex.: um município em um ano)."""

    def __init__(self):
        self.escolas = 0
        self.matriculas_total = 0
        self.aprovados = 0
        self.reprovados = 0
        self.abandono = 0

    def somar(self, registro):
        self.escolas += 1
        self.matriculas_total += registro.matriculas_total
        self.aprovados += registro.aprovados
        self.reprovados += registro.reprovados
        self.abandono += registro.abandono

    def base(self):
        # Padrão INEP: só alunos com situação final
        return self.aprovados + self.reprovados + self.abandono

    def _taxa(self, parte):
        # Base 0 (ex.: CEEJA): não dá para dividir, então não há taxa
        if self.base() == 0:
            return None
        return parte / self.base() * 100

    def taxa_aprovacao(self):
        return self._taxa(self.aprovados)

    def taxa_abandono(self):
        return self._taxa(self.abandono)

    def taxa_reprovacao(self):
        return self._taxa(self.reprovados)


def montar_hashes(linhas):
    """Monta os hashes sem repetidos a partir das linhas de todos os anos.

    municipios: {nome_normalizado: Municipio}
    escolas:    {(municipio_normalizado, escola_normalizada): Escola}
    """
    municipios = {}
    escolas = {}

    for linha in linhas:
        # 1. Município: CHECA se já existe; se não, cria e ADICIONA
        chave_municipio = normalizar(linha["NomeMunicipio"])
        if chave_municipio in municipios:
            municipio = municipios[chave_municipio]          # PEGA (reaproveita)
        else:
            municipio = Municipio(linha["NomeMunicipio"])
            municipios[chave_municipio] = municipio          # ADICIONA

        # 2. Escola: mesma ideia, com a chave (município, escola)
        chave_escola = (chave_municipio, normalizar(linha["NomeUnidadeEscolar"]))
        if chave_escola in escolas:
            escola = escolas[chave_escola]                   # PEGA (reaproveita)
        else:
            escola = Escola(linha["NomeUnidadeEscolar"])
            municipio.adicionar_escola(escola)
            escolas[chave_escola] = escola                   # ADICIONA

        # 3. O registro do ano sempre é novo e vai para a escola certa
        escola.adicionar_registro(criar_registro(linha))

    return municipios, escolas


def montar_totais(escolas):
    """Monta o hash {(municipio_normalizado, ano): Totais}.

    Soma primeiro (todas as escolas do município no ano) e divide depois (nas taxas).
    """
    totais = {}
    for escola in escolas.values():
        for registro in escola.registros:
            chave = (escola.municipio.nome_normalizado, registro.ano)
            if chave not in totais:
                totais[chave] = Totais()
            totais[chave].somar(registro)
    return totais


def buscar_na_lista(registros, municipio_normalizado, ano):
    """Mesma busca, mas SEM hash: percorre a lista inteira (O(n))."""
    resultado = Totais()
    for registro in registros:
        if registro.escola.municipio.nome_normalizado == municipio_normalizado and registro.ano == ano:
            resultado.somar(registro)
    return resultado


if __name__ == "__main__":
    from leitor_csv import ler_todos_anos

    linhas = ler_todos_anos()
    municipios, escolas = montar_hashes(linhas)

    total_registros = sum(len(e.registros) for e in escolas.values())
    print("Linhas lidas:", len(linhas))
    print("Municípios únicos:", len(municipios))
    print("Escolas únicas:", len(escolas))
    print("Registros dentro das escolas:", total_registros)

    exemplo = next(iter(escolas.values()))
    anos = [r.ano for r in exemplo.registros]
    print("Exemplo:", exemplo.nome, "| anos:", anos)
