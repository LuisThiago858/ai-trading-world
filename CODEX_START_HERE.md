# Prompt inicial — Codex Desktop

Leia integralmente `AGENTS.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/WORLD_3D.md`, `docs/ROADMAP.md` e `tasks/001-foundation.md`.

Estamos construindo **AI Trading World**, um **jogo 3D verdadeiro com câmera isométrica** sobre gerenciamento de um escritório de investimentos com agentes de IA e dinheiro 100% fictício. **A direção visual mudou: NÃO utilizar Phaser, pixel art 2D nem sprites para simular 3D.** A stack visual é React + TypeScript + Three.js + React Three Fiber + Drei, com `OrthographicCamera` e modelos 3D. O dashboard permanece em React.

Implemente **somente a Tarefa 001 — Fundação**. Entregue um monorepo executável com backend Django/DRF/PostgreSQL e frontend React/Vite/TypeScript; endpoints de criação/consulta de sessão demo (saldo inicial 10.000 USDT fictícios) e carteira; uma cena **3D isométrica graybox** com piso, paredes baixas, 3 mesas, monitores e avatares geométricos clicáveis para Alex, Maya e Victor; HUD React exibindo a carteira e o personagem selecionado; estados de erro/loading, fallback para WebGL indisponível e testes mínimos. A câmera deve ser ortográfica e orientada em ângulo isométrico. Não dependa de arquivos `.glb` externos nesta tarefa.

Não integrar LLM, LangGraph, CCXT, brokers, dados ao vivo, ordens reais ou simuladas, Celery nem WebSocket agora. Execute testes possíveis, documente comandos e limitações sem inventar resultados e apresente ao final: Contexto/Problema, Solução, Resultados, Arquivos alterados, Como rodar, Próximos passos. **Não faça commit automaticamente.**
