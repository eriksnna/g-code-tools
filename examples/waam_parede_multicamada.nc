(Exemplo de WAAM: parede reta, deposicao em 4 camadas)
(Dialeto: Generico - M3 liga o arco, M5 desliga - compativel com o perfil padrao)
(Troque o modo para "Deposicao" na barra superior para ver as metricas de cordao)

G21 G90
G0 Z0.5          ; altura inicial, um pouco acima da base

(=== camada 1, Z = 0 ===)
G0 X0 Y0
M3               ; abre o arco / inicia deposicao
G1 X0 Y0 Z0 F200
G1 X100 Y0 F200
M5               ; fecha o arco ao fim da camada
G4 P3            ; espera 3s para resfriar antes da proxima camada

(=== camada 2, Z = 2mm ===)
G0 X100 Y0 Z2
M3
G1 X100 Y0 Z2 F200
G1 X0 Y0 F200
M5
G4 P3

(=== camada 3, Z = 4mm ===)
G0 X0 Y0 Z4
M3
G1 X0 Y0 Z4 F200
G1 X100 Y0 F200
M5
G4 P3

(=== camada 4, Z = 6mm ===)
G0 X100 Y0 Z6
M3
G1 X100 Y0 Z6 F200
G1 X0 Y0 F200
M5

G0 Z20           ; retrai a tocha ao final
M2