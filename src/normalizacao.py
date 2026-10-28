import unicodedata


def remover_acentos(texto):
    """Tira os acentos: "Camapuã" -> "Camapua"."""
    # NFD separa a letra do acento: "ã" vira "a" + "~"
    separado = unicodedata.normalize("NFD", texto)
    sem_acento = ""
    for caractere in separado:
        # Mn = marca de acento; essas são descartadas
        if unicodedata.category(caractere) != "Mn":
            sem_acento += caractere
    return sem_acento


def normalizar(texto):
    """Regra fixa para comparar nomes: sem acento, maiúsculo, sem espaços sobrando."""
    texto = remover_acentos(texto)
    texto = texto.upper()
    # split() + join() tira espaços do início/fim e troca espaços duplos por um só
    texto = " ".join(texto.split())
    return texto
