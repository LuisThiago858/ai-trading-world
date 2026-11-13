# AGENTS.md — AI Trading World 3D

## Missão

Construir incrementalmente um **jogo 3D isométrico de verdade** sobre gerenciamento de investimentos com agentes de IA e exclusivamente capital virtual. Ler `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/WORLD_3D.md` e `docs/ROADMAP.md` antes de alterar o escopo.

## Produto e experiência — decisões definitivas

1. O escritório e os personagens são **malhas/objetos tridimensionais reais**, renderizados via Three.js/React Three Fiber. A câmera é **ortográfica** em vista isométrica, com iluminação, sombras e profundidade reais. Não substituir por sprites, Phaser 2D ou representação 2.5D.
2. Painéis de investimento, aprovações e relatórios são componentes React HTML acessíveis; o Canvas 3D fornece cenário e interações espaciais, não concentra todas as funcionalidades.
3. Personagens iniciais: Alex (análise técnica), Maya (estratégia), Victor (risco). Avatar não implica chamada contínua a modelo LLM.
4. Usar placeholders 3D geométricos na fundação: sem depender de modelos pagos, downloads manuais, APIs, plugins Blender ou serviços externos.
5. Animar e posicionar personagens a partir de estado/eventos tipados do backend. A cena 3D **nunca** deve ser a origem da verdade financeira.

## Segurança financeira — não negociável

6. Nunca conectar negociação real, pedir credenciais de corretora, movimentar fundos reais ou oferecer depósitos/saques. MVP é apenas simulação.
7. Agentes apenas analisam e propõem. Todo investimento novo exige aprovação explícita do jogador. Revalidar após aprovação e antes de criar/reservar ordem.
8. Motor de risco determinístico e independente de IA. O personagem Victor explica riscos, não substitui o motor e não pode ignorá-lo.
9. Usar `Decimal` no Python e `NUMERIC` no PostgreSQL para montantes, preços, quantidades e taxas financeiros persistidos; nunca `float`.
10. Ordem, fill, reserva e ledger devem ser idempotentes, auditáveis, com transações atômicas e isolamento entre sessões.
11. Replay/backtest nunca acessa dados futuros. Registrar snapshots, timestamps, fonte e versões.
12. Dados demo sempre rotulados como fictícios. Não inventar cotações atuais ou apresentar ganho como garantia.

## Stack-alvo

- Frontend: React, TypeScript, Vite, Three.js, `@react-three/fiber`, `@react-three/drei`.
- Assets: `.glb`/glTF e Blender quando houver modelos definitivos.
- Backend: Django, Django REST Framework, PostgreSQL.
- Futuro: Celery/Redis, Django Channels, LangGraph e coletor de dados públicos.
- Na versão inicial, preferir compatibilidade estável entre versões React, Three e R3F; verificar peers no momento da instalação, sem pinagem arbitrária de versões incompatíveis.

## Padrão de trabalho

- Trabalhar por tarefas pequenas; não tentar concluir todo o roadmap em uma interação.
- Antes de editar, resumir plano e arquivos envolvidos; depois implementar, executar testes realmente disponíveis e registrar limitações.
- Priorizar legibilidade, tipos, testes, performance, responsividade e fallback se WebGL não funcionar.
- Não fazer commits automaticamente sem solicitação do usuário. Ao finalizar, mostrar: **Contexto/Problema, Solução, Resultados, Arquivos alterados, Como testar, Próximos passos** e sugerir commit.
- Nunca incluir chaves reais ou arquivos `.env` com segredos em commit. Manter `.env.example`.

## Primeira tarefa

Executar `tasks/001-foundation.md`: criar sessão demo e **primeira cena 3D isométrica funcional (graybox)**. Não integrar IA, corretora, ordens nem assets finais ainda.
