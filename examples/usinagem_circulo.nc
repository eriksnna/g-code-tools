(Exemplo de usinagem: contorno circular usando arcos G2/G3)
(Dialeto: Generico - M3/M4 liga, M5 desliga)
(Demonstra interpolacao circular com I/J: centro relativo ao ponto inicial do arco)

G21 G90
G0 Z5
M3 S10000

(--- circulo 1: sentido horario (G2), raio 20mm, centro em X50 Y40 ---)
G0 X70 Y40
G1 Z-3 F120
G2 X70 Y40 I-20 J0 F500
G0 Z5

(--- circulo 2: sentido anti-horario (G3), raio 10mm, centro em X150 Y40 ---)
G0 X160 Y40
G1 Z-3 F120
G3 X160 Y40 I-10 J0 F500
G0 Z5

M5
G0 X0 Y0
M2