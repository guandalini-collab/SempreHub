# 🧭 MANIFESTO DE MARCA: SempreHub

> O projeto antes conhecido como **Udyama** foi oficialmente rebatizado como **SempreHub**.
> Este documento substitui a antiga documentação de branding e passa a ser a referência única da marca.

## 1. O Nome e a Nossa Razão de Existir

**SempreHub** nasce da união de duas ideias que definem o produto:

- **Sempre** — a continuidade. Empreender não é um evento isolado, é um ciclo que não para: cada turno
  exige nova decisão, nova leitura de mercado, nova reação ao imprevisto. A marca comunica permanência,
  constância e acompanhamento de longo prazo.
- **Hub** — o ponto de convergência. Não somos uma ferramenta solitária; somos o centro onde pessoas,
  capital, dados fiscais, estratégia e operação se encontram e se conectam.

Juntas, as duas metades afirmam a nossa tese: **o SempreHub representa um ecossistema dinâmico de
aceleração de negócios.** Dinâmico porque o ambiente muda a cada ciclo — regime tributário, demanda,
custo da folha, crises externas. Ecossistema porque nenhuma dessas variáveis existe isolada: mexer no
preço move o posicionamento, que move a demanda, que move o caixa, que move a confiança do fundador.
Aceleração porque o nosso papel não é apenas registrar o que aconteceu, mas encurtar o caminho entre a
decisão e o aprendizado.

## 2. Os Pilares da Marca

1. **Ecossistema, não planilha.** Mostramos consequência em cadeia, não números soltos.
2. **Dinamismo com rigor.** A simulação é viva, mas as regras são fiéis à realidade do negócio
   brasileiro — Simples Nacional, teto do MEI, Custo Brasil da folha, CMV sob pressão.
3. **Aceleração honesta.** Aceleramos o aprendizado, inclusive o aprendizado com o erro. O estado de
   sobrevivência não é escondido do usuário: é sinalizado.
4. **Clareza institucional.** Interface sóbria, leitura imediata, zero ruído decorativo.

## 3. Paleta de Cores Institucional

A identidade cromática é **mantida integralmente** na transição de marca — é o elo visual entre a
história do projeto e a nova fase.

| Cor | Hex | Papel na marca |
| --- | --- | --- |
| **Azul Profundo** | `#0B2545` | Cor primária. Confiança, solidez institucional e a seriedade da gestão financeira. Base de cabeçalhos, superfícies de destaque e tipografia principal. |
| **Ouro Fosco** | `#C5A059` | Cor de acento. Valor gerado, recompensa pelo esforço e energia de aceleração. Reservada a indicadores-chave, ações primárias e realces — nunca como fundo extenso. |
| **Branco Puro** | `#FFFFFF` | Respiro. Garante a limpeza estética esperada de uma aplicação moderna. |

**Regra de uso:** Azul Profundo estrutura, Ouro Fosco aponta. Se tudo é dourado, nada é importante.

## 4. Os Logotipos Oficiais

Os arquivos oficiais da marca ficam junto aos recursos visuais da aplicação, em
`frontend/src/assets/`:

| Arquivo | Caminho | Uso |
| --- | --- | --- |
| `SempreHub.jpg` | `frontend/src/assets/SempreHub.jpg` | Arte original (1024×1024, fundo branco). Fonte para gerar as demais versões. |
| `SempreHub.pdf` | `frontend/src/assets/SempreHub.pdf` | Mesma arte em PDF (imagem, não vetorial), para material institucional. |
| `logo-semprehub.png` | `frontend/src/assets/logo-semprehub.png` | Logo horizontal recortado, fundo transparente. É o arquivo usado na interface. |
| `icone-semprehub.png` | `frontend/src/assets/icone-semprehub.png` | Só o símbolo (rede), fundo transparente, para usos quadrados. |
| `favicon.png` | `frontend/public/favicon.png` | Símbolo em fundo branco (256×256), ícone da aba do navegador. |
| `semprehub-original.svg` | `frontend/public/marca/semprehub-original.svg` | Arquivo original enviado para comunicação; contém a arte em imagem incorporada, preservada sem alterações. Disponível em `/marca/semprehub-original.svg`. |

### Como a interface usa o logo

- **Tela de entrada:** logo horizontal grande (cerca de 260–290 px de largura), dentro do cartão branco.
- **Cabeçalho:** logo horizontal sobre uma placa branca com contorno em Ouro Fosco, ao lado da assinatura
  *Ecossistema de Aceleração de Negócios* (oculta em telas pequenas).

O logo original tem muito espaço em branco ao redor; por isso a interface usa a versão recortada. Sobre o Azul
Profundo, o logo fica sempre numa placa branca, porque o "Sempre" em azul-escuro perderia contraste direto sobre o fundo.

### Diretrizes de aplicação

- Preserve a proporção do logo. Não distorça. Use a versão recortada (`logo-semprehub.png`) em vez de reduzir o quadrado original.
- Mantenha uma área de respiro equivalente a pelo menos 25% da altura do logo ao seu redor.
- Sobre fundo escuro, aplique o logo numa placa branca, sem alterar suas cores.
- Não recolorize, não aplique sombras, gradientes ou contornos fora da paleta institucional.
