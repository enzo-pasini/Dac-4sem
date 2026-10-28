import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src")) # Tirar warning de importação local Pylance.

from leitor_csv import ler_csv
from modelos import RegistroAnual, linha_para_objetos

CAMINHO_2018 = os.path.join(
    os.path.dirname(__file__), "..", "dados", "csv",
    "matriculas-por-unidade-escolar-2018.csv",
)


class TestModelos(unittest.TestCase):

    def setUp(self):
        self.linhas = ler_csv(CAMINHO_2018)
        self.registros = [linha_para_objetos(linha) for linha in self.linhas]

    def test_uma_linha_vira_um_registro(self):
        self.assertEqual(len(self.registros), len(self.linhas))
        self.assertIsInstance(self.registros[0], RegistroAnual)

    def test_numeros_sao_int(self):
        r = self.registros[0]
        self.assertIsInstance(r.aprovados, int)
        self.assertEqual(r.aprovados, 585)

    def test_ligacao_para_cima_e_para_baixo(self):
        r = self.registros[0]
        escola = r.escola
        municipio = escola.municipio

        # Para cima
        self.assertEqual(municipio.nome, "Campo Grande")
        # Para baixo: os dois lados apontam para os mesmos objetos
        self.assertIn(escola, municipio.escolas)
        self.assertIn(r, escola.registros)


if __name__ == "__main__":
    unittest.main()
