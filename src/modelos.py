from normalizacao import normalizar


class Municipio:
    """Um município. Conhece as suas escolas (para baixo)."""

    def __init__(self, nome):
        self.nome = nome                          # original, para exibir
        self.nome_normalizado = normalizar(nome)  # para comparar
        self.escolas = []

    def adicionar_escola(self, escola):
        # Liga os dois lados ao mesmo tempo: para cima e para baixo
        escola.municipio = self
        self.escolas.append(escola)


class Escola:
    """Uma escola. Conhece o seu município (para cima) e os seus registros (para baixo)."""

    def __init__(self, nome):
        self.nome = nome                          # original, para exibir
        self.nome_normalizado = normalizar(nome)  # para comparar
        self.municipio = None
        self.registros = []

    def adicionar_registro(self, registro):
        # Liga os dois lados ao mesmo tempo: para cima e para baixo
        registro.escola = self
        self.registros.append(registro)


class RegistroAnual:
    """Os números de uma escola em um ano. Conhece a sua escola (para cima)."""

    def __init__(self, ano, matriculas_total, matricula_inicial, matricula_apos_censo,
                 transferidos, cancelados, falecido, abandono,
                 aprovados, reprovados, cursando, outras_situacoes):
        self.ano = ano
        self.matriculas_total = matriculas_total
        self.matricula_inicial = matricula_inicial
        self.matricula_apos_censo = matricula_apos_censo
        self.transferidos = transferidos
        self.cancelados = cancelados
        self.falecido = falecido
        self.abandono = abandono
        self.aprovados = aprovados
        self.reprovados = reprovados
        self.cursando = cursando
        self.outras_situacoes = outras_situacoes
        self.escola = None


def criar_registro(linha):
    """Cria o RegistroAnual de uma linha, convertendo os números de texto para int."""
    return RegistroAnual(
        ano=int(linha["AnoReferencia"]),
        matriculas_total=int(linha["MatriculasTotal"]),
        matricula_inicial=int(linha["MatriculaInicial"]),
        matricula_apos_censo=int(linha["MatriculaAposCenso"]),
        transferidos=int(linha["Transferidos"]),
        cancelados=int(linha["Cancelados"]),
        falecido=int(linha["Falecido"]),
        abandono=int(linha["Abandono"]),
        aprovados=int(linha["Aprovados"]),
        reprovados=int(linha["Reprovados"]),
        cursando=int(linha["Cursando"]),
        outras_situacoes=int(linha["OutrasSituacoes"]),
    )


def linha_para_objetos(linha):
    """Transforma um dicionário (uma linha do CSV) nos 3 objetos ligados.

    Aqui cada linha cria o seu próprio Municipio e Escola.
    A versão sem repetidos (com hash) está em estruturas.py.
    """
    municipio = Municipio(linha["NomeMunicipio"])
    escola = Escola(linha["NomeUnidadeEscolar"])
    registro = criar_registro(linha)

    municipio.adicionar_escola(escola)
    escola.adicionar_registro(registro)
    return registro


if __name__ == "__main__":
    from leitor_csv import ler_csv

    linhas = ler_csv("dados/csv/matriculas-por-unidade-escolar-2018.csv")
    registros = [linha_para_objetos(linha) for linha in linhas]
    print("RegistroAnual criados:", len(registros))

    r = registros[0]
    print("Ano:", r.ano, "| Aprovados:", r.aprovados)
    print("Escola (para cima):", r.escola.nome)
    print("Município (para cima):", r.escola.municipio.nome)
