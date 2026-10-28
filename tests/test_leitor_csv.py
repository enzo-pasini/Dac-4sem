import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from leitor_csv import ler_csv

CAMINHO_2018 = os.path.join(
    os.path.dirname(__file__), "..", "dados", "csv",
    "matriculas-por-unidade-escolar-2018.csv",
)


class TestLeitorCsv(unittest.TestCase):

    def test_quantidade_igual_linhas_do_arquivo(self):
        # Conta as linhas "cruas" do arquivo e tira 1 (o cabeçalho)
        with open(CAMINHO_2018, encoding="utf-8") as arquivo:
            linhas_no_arquivo = sum(1 for _ in arquivo) - 1

        registros = ler_csv(CAMINHO_2018)
        self.assertEqual(len(registros), linhas_no_arquivo)

    def test_chaves_vem_do_cabecalho(self):
        registros = ler_csv(CAMINHO_2018)
        self.assertIn("NomeMunicipio", registros[0])
        self.assertIn("Aprovados", registros[0])


if __name__ == "__main__":
    unittest.main()
