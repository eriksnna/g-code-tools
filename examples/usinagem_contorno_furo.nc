(Exemplo de usinagem: contorno retangular com furo central)
(Dialeto: Generico - M3/M4 liga, M5 desliga - compativel com o perfil padrao)
(Unidades em milimetros, coordenadas absolutas)

G21 G90          ; milimetros, coordenadas absolutas
G0 Z5            ; altura de seguranca, acima da peca
M3 S8000         ; liga o spindle a 8000 RPM

(--- contorno retangular, 60x40mm, profundidade 5mm ---)
G0 X10 Y10
G1 Z-5 F150      ; desce cortando
G1 X70 Y10 F600
G1 X70 Y50
G1 X10 Y50
G1 X10 Y10
G0 Z5            ; sobe antes de deslocar

(--- furo central, profundidade 8mm ---)
G0 X40 Y30
G1 Z-8 F100
G4 P1            ; espera 1s no fundo do furo, limpa cavaco
G0 Z5

M5               ; desliga o spindle
G0 X0 Y0
M2               ; fim do programa