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
| `SempreHub.jpg` | `frontend/src/assets/SempreHub.jpg` | Logo de tela (1024×1024). É o arquivo consumido pela interface. |
| `SempreHub.pdf` | `frontend/src/assets/SempreHub.pdf` | Versão vetorial/impressa. Material institucional, apresentações e aplicações em alta resolução. |

### Como a interface consome o logo

Os componentes da interface (`frontend/src/componentes/ui.tsx` e a tela de entrada) importam o arquivo pelo próprio pipeline do Vite, de modo que o hash e o caminho final de
build sejam resolvidos automaticamente:

```tsx
import logoSempreHub from "./assets/SempreHub.jpg";

<img src={logoSempreHub} alt="Logotipo SempreHub" className="h-14 w-14 rounded-lg object-contain" />
```

O logo é exibido na tela de entrada e no cabeçalho de todas as páginas, imediatamente à esquerda do título
**SempreHub** e da assinatura *Ecossistema de Aceleração de Negócios*. Uma cópia em `frontend/public/favicon.jpg`
é usada como ícone da aba do navegador.

No Tailwind, as cores institucionais estão disponíveis como `marinho` (`#0B2545`) e `ouro` (`#C5A059`).

### Diretrizes de aplicação

- Preserve a proporção quadrada original (1:1). Não distorça, não recorte.
- Mantenha uma área de respiro equivalente a pelo menos 25% da altura do logo ao seu redor.
- Sobre fundo escuro, use o logo como está — ele foi desenhado para conviver com o Azul Profundo.
- Não recolorize, não aplique sombras, gradientes ou contornos fora da paleta institucional.
