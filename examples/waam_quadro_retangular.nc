(Exemplo de WAAM: quadro retangular, deposicao em 3 camadas)
(Dialeto: Generico - M3 liga o arco, M5 desliga)
(Cada camada percorre o mesmo contorno fechado, subindo 2.5mm por camada)

G21 G90
G0 Z1
G0 X0 Y0

(=== camada 1, Z = 0 ===)
M3
G1 X0 Y0 Z0 F180
G1 X80 Y0 F180
G1 X80 Y60 F180
G1 X0 Y60 F180
G1 X0 Y0 F180
M5
G4 P4            ; resfriamento entre camadas

(=== camada 2, Z = 2.5mm ===)
G0 Z2.5
M3
G1 X0 Y0 Z2.5 F180
G1 X80 Y0 F180
G1 X80 Y60 F180
G1 X0 Y60 F180
G1 X0 Y0 F180
M5
G4 P4

(=== camada 3, Z = 5mm ===)
G0 Z5
M3
G1 X0 Y0 Z5 F180
G1 X80 Y0 F180
G1 X80 Y60 F180
G1 X0 Y60 F180
G1 X0 Y0 F180
M5

G0 Z25           ; retrai a tocha
M2