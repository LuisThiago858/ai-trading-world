# Especificação da experiência 3D isométrica

## Definição visual

O jogo é **3D verdadeiro**. A câmera ortográfica cria a aparência isométrica típica de jogos de gerenciamento, mas piso, paredes, móveis, monitores e personagens possuem geometria e profundidade reais. O jogo não será criado com imagens 2D, sprite sheets nem técnica 2.5D.

## Câmera

- `OrthographicCamera` fixa em visão diagonal elevada; enquadrar o escritório inteiro na primeira entrega.
- Posição inicial sugerida para protótipo: `(10, 12, 10)`, olhando para `(0, 0, 0)`; calibrar para a composição ficar isométrica.
- Permitir zoom com limites; pan limitado para não perder o cenário. Rotação de câmera é uma melhoria futura (não requisito do MVP).
- O visual deve preservar a escala relativa dos objetos e usar luzes e sombras suaves.

## Cena inicial — escritório graybox

- Base/piso 3D retangular, paredes baixas ou recortadas para não ocultar mesas.
- Três estações de trabalho com mesas e monitores simples (meshes).
- Alex, Maya e Victor representados por avatares 3D geométricos distintos com cores/etiquetas.
- Clicar em um avatar realça sua posição e atualiza um painel HTML React com nome, função e status.
- Estado inicial dos três: `idle`; possível animação simples de flutuação/realce apenas estética.
- Criar HUD com capital e saldo em USDT fictícios; exibir cena de erro amigável se WebGL indisponível.
- Usar geometria gerada por código na tarefa 001, sem exigir modelos 3D externos.

## Experiência posterior

1. Modelagem low-poly/cozy stylized em Blender e exportação `.glb`/glTF.
2. Personagens com clips `idle`, `typing`, `walking`, `meeting`, `celebrating`, `concerned`, conforme animações realmente disponíveis.
3. Pontos de interesse clicáveis (mesa, sala de reunião, terminal de operações).
4. Deslocamento por waypoints/navmesh com sincronização por estado; não iniciar caminho pelo retorno de cada token de LLM.
5. Salas adicionais (análise, reunião, operações, laboratório).
6. Efeitos/partículas e mudanças de iluminação parcimoniosos, com opções de qualidade.

## Contratos de interação

- Clique em avatar: muda seleção local e exibe ficha; **não** dispara uma nova ordem.
- Clique em proposta no HUD: abre detalhes e chama API de aprovação apenas após interação explícita.
- Evento do backend: atualiza estado visual correspondente, sem alterar operações financeiras.
- Se o Canvas falhar, o HUD e o acesso à carteira continuam disponíveis.

## Qualidade e performance

- Priorizar desktop, considerar notebooks comuns com GPU integrada.
- Reaproveitar geometrias/materiais, evitar luzes dinâmicas caras, limitar sombras e DPR.
- Adicionar lazy loading/level of detail quando os assets aumentarem.
- Garantir componentes de navegação e aprovação acessíveis sem depender de raycasting.

## Critérios visuais de aceite da cena inicial

- Ver o piso, paredes, três mesas, três monitores e três personagens como volumes 3D reais.
- A câmera mostra o escritório de maneira isométrica, não top-down plano nem primeira pessoa.
- É possível clicar nos três personagens e ver seus detalhes no painel HTML.
- Redimensionar janela mantém a cena enquadrada e não quebra o HUD.
- A aplicação oferece fallback quando WebGL não estiver disponível.
