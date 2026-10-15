## G-Code Tools

### Sobre

Modernização e acessibilidade em sistemas CNC utilizados para impressão 3D de componentes metálicos: desenvolvimento de ferramenta independente e plugin nativo para o ecossistema mach3.

### 21/07 — terça-feira ~ 6 horas

- **definição do projeto:** modernização e acessibilidade em sistemas CNC utilizados para impressão 3D de componentes metálicos: desenvolvimento de ferramenta independente e plugin nativo para o ecossistema mach3. o projeto será desenvolvido em duas frentes tecnológicas complementares para otimizar ferramentas de trabalho em manufatura aditiva / impressão 3D.
	
	- **parte 1 -** visualizador independente: desenvolvimento de um aplicativo nativo focado na visualização avançada de G-Code do percurso de impressão 3D, contando com uma interface 2D e 3D altamente intuitiva. o desenvolvimento prevê escalabilidade arquitetural para uma possível ramificação futura voltada à própria geração de instruções G-Code.
	
	- **parte 2 -** integração legada: desenvolvimento de um plugin nativo em C++ injetável no software legado mach3. este módulo permitirá a visualização e teste das trajetórias de corte em tempo real (animações 2D e 3D integradas à memória da máquina), criando a base tecnológica para uma possível renovação completa da interface gráfica (GUI) original do sistema.

### 23/07 — quinta-feira ~ 7 horas

- reunião com cliente | definição de objetivo, escopo e limitações:

o cliente principal e orientador técnico da demanda é o Prof. Dr. Gustavo Henrique, do   **[Manufacturing Technologies Research Laboratory](https://www.dief.unifi.it/vp-207-about.html)** da **Universita degli Studi Firenze** (Itália).

o projeto é destinado diretamente aos alunos, pesquisadores e educadores de universidades por todo o Brasil (e exterior) que dependem do mach3 ou de outras ferramentas CNC para ensino e realização de impressão 3D. atualmente, os softwares de simulação e controle CNC disponíveis no mercado apresentam três grandes barreiras: são datados, possuem licenças pagas de alto custo, ou são de difícil acesso para instituições de ensino e estudantes. o objetivo principal deste projeto é democratizar o acesso à tecnologia de ponta na manufatura, facilitando o uso dessas ferramentas através de interfaces modernas e introduzindo no mercado um novo projeto acessível, seguro e de alto impacto educacional.

### 24/07 — sexta-feira ~ 6 horas

- escolha das ferramentas da parte 1:
	- **para o aplicativo independente (parte 1):** desenvolvimento estruturado em Python, aproveitando a alta eficiência da linguagem para o processamento e parsing de arquivos de texto (G-Code). A interface gráfica de usuário (GUI) e o motor de renderização 3D serão construídos utilizando frameworks robustos do ecossistema Python (como PyQt/PySide para a estruturação nativa das janelas, operando em conjunto com PyOpenGL ou bibliotecas de visualização espacial para a renderização fluida das trajetórias de corte).

### 27/07 — segunda-feira ~ 8 horas

- Teste prático com numpy. **(Sem Parser)**

### 1/08 — sábado / 2/08 — domingo ~ 17 horas

1. Removido o `plot_mock_gcode` e a geração com NumPy da espiral.

2. Adicionado GCodeParser, que:
    - remove comentários (; e ( ... )) e normaliza a linha;
    - extrai pares letra + número (X10.5, G1, F300);
    - mantém o estado modal: modo de movimento (G0/G1/G2/G3), coordenadas absolutas ou incrementais (G90/G91) e unidades (G20 polegadas / G21 mm);
    - converte arcos G2/G3 (centro dado por I/J, plano XY) em pequenos segmentos;
    - separa os movimentos em cortes (G1/G2/G3) e rápidos (G0).

3. Botão agora abre um diálogo para escolher o arquivo.

4. Duas linhas na cena: vermelha translúcida para rápidos, azul para cortes. O modo "lines" desenha cada segmento separadamente.

5. Câmera centralizada no centro da bounding box da peça, com distância proporcional ao tamanho.

6. Limpeza dos itens anteriores antes de cada novo carregamento.

7. Status na tela com a contagem de segmentos e de avisos de parsing.
	
