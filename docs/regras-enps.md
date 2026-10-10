# eNPS determinístico — item 5

A nota é recalculada a cada rodada a partir de 7, sem acumular bônus antigos ou sortear números. Condições iguais dentro de um mesmo perfil geram notas iguais. Perfis Padrão, Exigente e Engajado têm sensibilidades diferentes, sem aleatoriedade. Resultados extremos continuam possíveis. Não representa pesquisa com pessoas reais.

Referência salarial positiva definida pelo professor: acima, +1; abaixo, -2; igual, zero. Referência zero não permite comparação de mercado e não gera bônus ou penalidade salarial.

Benefício de pelo menos R$ 150 por funcionário por rodada: +1. O campo já representa valor por funcionário; a despesa permanece quantidade de funcionários x valor individual. Valores menores continuam opcionais, têm custo e mantêm os demais efeitos de clima existentes, mas não concedem esse ponto no eNPS.

Horas extras em duas ou mais rodadas consecutivas com funcionários: -1. Rodada sem horas extras ou sem funcionários reinicia a sequência. A nota permanece entre 0 e 10; nota >= 9 promotores, 7 <= nota < 9 neutros, nota < 7 detratores (adaptação fracionária didática). Todos os ativos são respondentes simulados. Zero funcionários: Não se aplica.

O cálculo é compartilhado pelos modelos Tradicional e Startup, sem mudanças em tabelas nem recálculo de resultados históricos.

Perfis: Padrão=max(1, total*2//5) quando total>0; Exigente=total*2//5; Engajado=resíduo. Exigente multiplica penalidades salariais e de horas extras por 1,5; Engajado multiplica bônus salariais e de benefício por 1,5. Todos começam com 7. enps_nota mantém compatibilidade como média ponderada; enps_perfis registra quantidades e notas. O eNPS conserva casas decimais e snapshots anteriores não são alterados.
