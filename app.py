"""Dashboard Streamlit. Rode com:  streamlit run app.py

Layout baseado no template https://github.com/dataprofessor/population-dashboard
(barra lateral + 3 colunas: indicadores | mapa e gráficos | ranking e explicações).
"""
import json
import os
import sys

import altair as alt
import streamlit as st

# Adiciona a pasta src/ ao caminho de busca, para o Python achar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from banco import (ANOS_TAXA_ABANDONO, ANOS_TAXA_APROVACAO, conectar,
                   evolucao_estado, taxas_todos_municipios)
from normalizacao import normalizar

TODO_ESTADO = "Todo o MS"
ANO_BASE = ANOS_TAXA_APROVACAO[0]                    # 2018: ano de comparação
CAMINHO_MAPA = os.path.join(os.path.dirname(__file__), "dados", "geo", "ms-municipios.json")
LINK_SEM_TAXA = "[Por que não há taxa?](#sem-taxa)"  # leva até a explicação na coluna 3

# Posições de cada coluna na linha (ano, escolas, matriculas, aprov, reprov, aband)
ANO, ESCOLAS, MATRICULAS, APROVACAO, REPROVACAO, ABANDONO = 0, 1, 2, 3, 4, 5

#######################
# Configuração da página
st.set_page_config(
    page_title="Educação Pública em MS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded")

#######################
# CSS: cards dos indicadores com fundo cinza e texto centralizado (igual ao template)
st.markdown("""
<style>
[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
}
[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
    border-radius: 8px;
}
[data-testid="stMetricLabel"] {
    display: flex;
    justify-content: center;
    align-items: center;
}
[data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

#######################
# Carregar dados do banco (uma consulta para todos os municípios, outra para o estado)
conexao = conectar()
linhas_municipios = taxas_todos_municipios(conexao)
linhas_estado = evolucao_estado(conexao)
conexao.close()

# Hash {(municipio_normalizado, ano): linha} -> busca O(1) de qualquer cidade/ano
por_municipio_ano = {}
nome_por_chave = {}                                  # {municipio_normalizado: nome original}
for chave, nome, *linha in linhas_municipios:
    por_municipio_ano[(chave, linha[ANO])] = linha
    nome_por_chave[chave] = nome

anos = sorted({linha[ANO] for linha in linhas_estado})   # 2025 não existe na fonte

#######################
# Barra lateral (filtros)
with st.sidebar:
    st.title("🎓 Educação Pública em MS")
    st.caption("Rede pública estadual · ODS 4 · 2018–2026")

    chave_por_nome = {nome: chave for chave, nome in nome_por_chave.items()}
    nomes = [TODO_ESTADO] + sorted(chave_por_nome, key=normalizar)
    escolha = st.selectbox("Município", nomes)

    anos_desc = anos[::-1]                           # mais recente primeiro
    ano = st.selectbox("Ano", anos_desc, index=anos_desc.index(ANOS_TAXA_APROVACAO[-1]))

    temas = ["blues", "greens", "viridis", "cividis", "plasma", "turbo"]
    tema = st.selectbox("Cores do mapa", temas)

    st.caption(f"Aprovação/reprovação válidas só em {ANOS_TAXA_APROVACAO[0]}–"
               f"{ANOS_TAXA_APROVACAO[-1]}; abandono só em {ANOS_TAXA_ABANDONO[0]}.")

# Hash {ano: linha} do que foi escolhido (estado inteiro ou um município)
if escolha == TODO_ESTADO:
    chave_escolhida = None
    por_ano = {linha[ANO]: linha for linha in linhas_estado}
else:
    chave_escolhida = chave_por_nome[escolha]
    por_ano = {a: por_municipio_ano[(chave_escolhida, a)] for a in anos
               if (chave_escolhida, a) in por_municipio_ano}


#######################
# Funções de formatação
def formatar_taxa(valor):
    return "não disponível" if valor is None else f"{valor:.1f}%"


def formatar_numero(numero):
    return f"{numero:,}".replace(",", ".")           # 1234567 -> 1.234.567


def diferenca_taxa(antes, depois):
    if antes is None or depois is None:
        return None
    return f"{depois - antes:+.1f} p.p. vs {ANO_BASE}"   # p.p. = pontos percentuais


def valor(ano_busca, coluna):
    """Valor de uma coluna para um ano; None se o município não tem dados nesse ano."""
    linha = por_ano.get(ano_busca)
    return None if linha is None else linha[coluna]


#######################
# Gráficos (Altair recebe listas de dicionários, sem pandas)

def fazer_donut(percentual, texto, cor):
    """Gráfico de rosca com o percentual no meio (igual ao template)."""
    cores = {"verde": ["#27AE60", "#12783D"], "vermelho": ["#E74C3C", "#781F16"]}[cor]
    dados = alt.Data(values=[{"Parte": texto, "Valor": percentual},
                             {"Parte": "", "Valor": 100 - percentual}])
    escala = alt.Scale(domain=[texto, ""], range=cores)
    rosca = alt.Chart(dados).mark_arc(innerRadius=45, cornerRadius=20).encode(
        theta="Valor:Q",
        color=alt.Color("Parte:N", scale=escala, legend=None),
    ).properties(width=130, height=130)
    numero = alt.Chart(alt.Data(values=[{}])).mark_text(
        fontSize=26, fontWeight=700, color=cores[0]
    ).encode(text=alt.value(f"{percentual:.1f}%"))
    return rosca + numero


def fazer_mapa(ano_mapa):
    """Mapa dos municípios coloridos pela taxa de aprovação do ano."""
    with open(CAMINHO_MAPA, encoding="utf-8") as arquivo:
        regioes = json.load(arquivo)["features"]

    # Junta o mapa com o banco usando o nome normalizado como chave do hash
    for regiao in regioes:
        chave = normalizar(regiao["properties"]["name"])
        linha = por_municipio_ano.get((chave, ano_mapa))
        regiao["properties"]["chave"] = chave
        regiao["properties"]["aprovacao"] = None if linha is None else linha[APROVACAO]

    # Camada 1: todos os municípios em cinza (= sem taxa)
    # Camada 2: por cima, só os que têm taxa, coloridos
    dados = alt.Data(values=regioes)
    dica = [alt.Tooltip("properties.name:N", title="Município"),
            alt.Tooltip("properties.aprovacao:Q", title="Aprovação (%)", format=".1f")]
    fundo = alt.Chart(dados).mark_geoshape(
        fill="#555555", stroke="#111111", strokeWidth=0.4
    ).encode(tooltip=dica).project(type="mercator")
    cores = alt.Chart(dados).mark_geoshape(stroke="#111111", strokeWidth=0.4).encode(
        color=alt.Color("properties.aprovacao:Q", title="Aprovação (%)",
                        scale=alt.Scale(scheme=tema)),
        tooltip=dica,
    ).transform_filter("isValid(datum.properties.aprovacao)").project(type="mercator")
    mapa = (fundo + cores).properties(height=380)

    # Contorno rosa no município escolhido
    escolhido = [r for r in regioes if r["properties"]["chave"] == chave_escolhida]
    if escolhido:
        mapa += alt.Chart(alt.Data(values=escolhido)).mark_geoshape(
            fill=None, stroke="#f63366", strokeWidth=3).project(type="mercator")
    return mapa


def fazer_evolucao():
    """Linhas de aprovação e reprovação por ano, com legenda grande e faixa 'sem dados'."""
    pontos = []
    for a in anos:
        for serie, coluna in (("Aprovação", APROVACAO), ("Reprovação", REPROVACAO)):
            if valor(a, coluna) is not None:
                pontos.append({"Ano": a, "Série": serie, "Taxa": round(valor(a, coluna), 1)})

    # A mesma escala de anos em todas as camadas (senão o eixo começa no 0)
    escala_anos = alt.Scale(domain=[anos[0] - 0.5, anos[-1] + 0.5], zero=False, nice=False)
    linhas = alt.Chart(alt.Data(values=pontos)).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X("Ano:Q", scale=escala_anos,
                axis=alt.Axis(format="d", values=anos, labelFontSize=13, title=None)),
        y=alt.Y("Taxa:Q", scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(title="%", labelFontSize=13, titleFontSize=13)),
        color=alt.Color("Série:N",
                        scale=alt.Scale(domain=["Aprovação", "Reprovação"],
                                        range=["#27AE60", "#E74C3C"]),
                        legend=alt.Legend(orient="top", title=None, labelFontSize=16,
                                          symbolSize=400, symbolStrokeWidth=5)),
        tooltip=["Ano:Q", "Série:N", alt.Tooltip("Taxa:Q", format=".1f")],
    )

    # Faixa cinza nos anos sem taxa (2024 a 2026), com aviso escrito
    ultimo_valido = ANOS_TAXA_APROVACAO[-1]
    faixa_dados = alt.Data(values=[{"inicio": ultimo_valido + 0.5, "fim": anos[-1] + 0.5,
                                    "texto": "Sem taxa (veja ❓ ao lado)"}])
    faixa = alt.Chart(faixa_dados).mark_rect(color="#888888", opacity=0.2).encode(
        x=alt.X("inicio:Q", scale=escala_anos), x2="fim:Q")
    aviso = alt.Chart(faixa_dados).mark_text(
        dy=-120, fontSize=13, color="#dddddd"
    ).encode(x=alt.X("media:Q", scale=escala_anos), text="texto:N").transform_calculate(
        media="(datum.inicio + datum.fim) / 2")

    # Linha vertical no ano escolhido
    marcador = alt.Chart(alt.Data(values=[{"Ano": ano}])).mark_rule(
        color="#f63366", strokeDash=[4, 4]).encode(x=alt.X("Ano:Q", scale=escala_anos))

    return (faixa + aviso + marcador + linhas).properties(height=300)


def fazer_heatmap():
    """Aprovação de cada município (colunas) em cada ano (linhas)."""
    celulas = [{"Município": nome_por_chave[chave], "Ano": a, "Aprovação": linha[APROVACAO]}
               for (chave, a), linha in por_municipio_ano.items()]
    base = alt.Chart(alt.Data(values=celulas)).encode(
        y=alt.Y("Ano:O", axis=alt.Axis(title=None, labelAngle=0, labelFontSize=12)),
        x=alt.X("Município:N", axis=alt.Axis(title=None, labelFontSize=9, labelAngle=-60)),
        tooltip=["Município:N", "Ano:O", alt.Tooltip("Aprovação:Q", format=".1f")],
    )
    # Igual ao mapa: células cinza embaixo (sem taxa), coloridas por cima
    fundo = base.mark_rect(color="#555555", stroke="black", strokeWidth=0.25)
    cores = base.mark_rect(stroke="black", strokeWidth=0.25).encode(
        color=alt.Color("Aprovação:Q", scale=alt.Scale(scheme=tema), legend=None),
    ).transform_filter("isValid(datum['Aprovação'])")
    return (fundo + cores).properties(height=260)


#######################
# Painel principal: 3 colunas, como no template
col = st.columns((1.6, 4.4, 2), gap="medium")

with col[0]:
    st.markdown(f"#### {escolha} · {ano}")

    aprov_base, aprov_ano = valor(ANO_BASE, APROVACAO), valor(ano, APROVACAO)
    st.metric("Taxa de aprovação", formatar_taxa(aprov_ano),
              diferenca_taxa(aprov_base, aprov_ano) if ano != ANO_BASE else None,
              help="Aprovados / (Aprovados + Reprovados + Abandono)")
    if aprov_ano is None:
        st.caption(LINK_SEM_TAXA)

    mat_base, mat_ano = valor(ANO_BASE, MATRICULAS), valor(ano, MATRICULAS)
    if mat_ano is None:
        st.metric("Matrículas", "sem escolas")
    else:
        delta_mat = None
        if mat_base and ano != ANO_BASE:
            delta_mat = f"{(mat_ano - mat_base) / mat_base * 100:+.1f}% vs {ANO_BASE}"
        st.metric("Matrículas", formatar_numero(mat_ano), delta_mat,
                  help="Válidas em todos os anos (2018–2026).")

    ano_abandono = ANOS_TAXA_ABANDONO[0]
    st.metric(f"Abandono em {ano_abandono}", formatar_taxa(valor(ano_abandono, ABANDONO)),
              help="Único ano com abandono confiável: sem comparação possível.")

    st.markdown("#### Situação final")
    col_donut = st.columns((0.2, 1, 0.2))
    with col_donut[1]:
        reprov_ano = valor(ano, REPROVACAO)
        if aprov_ano is None or reprov_ano is None:
            st.caption(f"Sem taxas em {ano}. {LINK_SEM_TAXA}")
        else:
            st.write("Aprovação")
            st.altair_chart(fazer_donut(aprov_ano, "Aprovação", "verde"))
            st.write("Reprovação")
            st.altair_chart(fazer_donut(reprov_ano, "Reprovação", "vermelho"))

with col[1]:
    st.markdown(f"#### Taxa de aprovação por município · {ano}")
    st.altair_chart(fazer_mapa(ano), width="stretch")
    if ano not in ANOS_TAXA_APROVACAO:
        st.caption(f"Mapa todo cinza: {ano} não tem taxa. {LINK_SEM_TAXA}")
    st.caption("Cinza = sem taxa. Paraíso das Águas (criado em 2013) não aparece no mapa base.")

    st.markdown(f"#### Evolução · {escolha}")
    st.altair_chart(fazer_evolucao(), width="stretch")

    st.markdown("#### Aprovação de cada município por ano")
    st.altair_chart(fazer_heatmap(), width="stretch")

with col[2]:
    st.markdown(f"#### Ranking · {ano}")

    ranking = [{"Município": nome_por_chave[chave],
                "Aprovação": linha[APROVACAO],
                "Matrículas": linha[MATRICULAS]}
               for (chave, a), linha in por_municipio_ano.items() if a == ano]
    # Ordena pela aprovação (maior primeiro); sem taxa -> ordena pelas matrículas
    ranking.sort(key=lambda m: (m["Aprovação"] or -1, m["Matrículas"]), reverse=True)

    st.dataframe(
        ranking,
        hide_index=True,
        height=420,
        column_config={
            "Município": st.column_config.TextColumn("Município"),
            "Aprovação": st.column_config.ProgressColumn(
                "Aprovação", format="%.1f%%", min_value=0, max_value=100),
            "Matrículas": st.column_config.NumberColumn("Matrículas", format="localized"),
        })

    st.subheader("❓ Por que 2024 e 2026 não têm taxa?", anchor="sem-taxa")
    st.markdown("""
- **2024:** cerca de 84% dos alunos ainda aparecem como *Cursando*
  (184.949 de 220.926). O resultado final não foi registrado, e 379 de 461
  escolas não têm nenhum aprovado, reprovado ou abandono.
- **2025:** não existe arquivo na fonte.
- **2026:** o ano letivo ainda não terminou: 0 aprovados, 0 reprovados, 0 abandonos.
- **Abandono:** só 2018 é confiável. Em 2019 caiu 98,5% em um ano
  (10.490 → 158), provável erro de digitação; de 2020 em diante é sempre 0.

Mostrar 0% seria informação falsa, por isso aparece **"não disponível"**.
As **matrículas** valem para todos os anos.
""")

    with st.expander("Sobre", expanded=True):
        st.markdown("""
- Dados: [dados.ms.gov.br – Matrículas por unidade escolar](https://www.dados.ms.gov.br/dataset/matriculas-por-unidade-escolar)
- :orange[**Taxa de aprovação**]: aprovados / (aprovados + reprovados + abandono), padrão INEP.
- :orange[**Agregação**]: soma os alunos das escolas primeiro e divide depois.
- :orange[**p.p.**]: pontos percentuais em relação a 2018.
""")
