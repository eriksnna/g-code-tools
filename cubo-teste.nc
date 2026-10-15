; cubo wireframe 20 x 20 x 20 mm
; base em Z=0 (sobre o grid), topo em Z=20
G21 ; unidades em mm
G90 ; coordenadas absolutas
G17 ; plano XY

; --- 1. contorno superior (Z=20) ---
G0 Z25
G0 X0 Y0
G0 Z20
G1 X20 Y0 F400
G1 X20 Y20
G1 X0 Y20
G1 X0 Y0

; --- 2. aresta vertical em (0,0) + contorno inferior (Z=0) ---
G1 Z0 F200
G1 X20 Y0 F400
G1 X20 Y20
G1 X0 Y20
G1 X0 Y0

; --- 3. aresta vertical em (20,0) ---
G0 Z25
G0 X20 Y0
G0 Z20
G1 Z0 F200

; --- 4. aresta vertical em (20,20) ---
G0 Z25
G0 X20 Y20
G0 Z20
G1 Z0 F200

; --- 5. aresta vertical em (0,20) ---
G0 Z25
G0 X0 Y20
G0 Z20
G1 Z0 F200

; retorno à segurança
G0 Z25
G0 X0 Y0
M2