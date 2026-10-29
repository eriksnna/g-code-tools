(Exemplo de usinagem: furacao em grade 3x2)
(Dialeto: Generico - M3/M4 liga, M5 desliga)

G21 G90
G0 Z5
M3 S6000

(--- furo 1 ---)
G0 X20 Y20
G1 Z-6 F100
G4 P0.5
G0 Z5

(--- furo 2 ---)
G0 X50 Y20
G1 Z-6 F100
G4 P0.5
G0 Z5

(--- furo 3 ---)
G0 X80 Y20
G1 Z-6 F100
G4 P0.5
G0 Z5

(--- furo 4 ---)
G0 X20 Y50
G1 Z-6 F100
G4 P0.5
G0 Z5

(--- furo 5 ---)
G0 X50 Y50
G1 Z-6 F100
G4 P0.5
G0 Z5

(--- furo 6 ---)
G0 X80 Y50
G1 Z-6 F100
G4 P0.5
G0 Z5

M5
G0 X0 Y0
M2