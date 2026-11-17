"""Instala o X-13ARIMA-SEATS oficial (U.S. Census Bureau, build 62) em /opt/x13.

Usado na construção da imagem do servidor. Uma falha não interrompe a
construção: o Dockerfile tenta em seguida o pacote x13binary (reserva).
"""
import io
import os
import stat
import tarfile
import urllib.request

URL = ("https://www2.census.gov/software/x-13arima-seats/x13as/unix-linux/"
       "program-archives/x13as_ascii-v1-1-b62.tar.gz")

try:
    dados = urllib.request.urlopen(URL, timeout=60).read()
    with tarfile.open(fileobj=io.BytesIO(dados)) as tar:
        membro = next(m for m in tar.getmembers() if m.isfile() and os.path.basename(m.name) == "x13as_ascii")
        conteudo = tar.extractfile(membro).read()
    os.makedirs("/opt/x13", exist_ok=True)
    destino = "/opt/x13/x13as_ascii"
    with open(destino, "wb") as arquivo:
        arquivo.write(conteudo)
    os.chmod(destino, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    print("X-13 oficial (b62) instalado em", destino)
except Exception as erro:  # rede indisponível ou arquivo diferente do esperado
    print("X-13 oficial indisponível:", erro)
