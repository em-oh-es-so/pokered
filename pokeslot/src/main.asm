SECTION "Entry", ROM0[$100]
    nop
    jp Boot
    ds $150 - @, 0

SECTION "Program", ROM0[$150]
Boot:
    di
    ld sp, $dfff
    xor a
    ldh [$ff], a
.waitVBlank
    ldh a, [$44]
    cp 144
    jr c, .waitVBlank
    xor a
    ldh [$40], a
    ldh [$42], a
    ldh [$43], a
    ldh [$26], a
    ld hl, $8000
    ld de, Tiles
    ld bc, TilesEnd - Tiles
.copyTiles
    ld a, [de]
    inc de
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .copyTiles
    ld hl, $9800
    ld bc, 1024
.clearMap
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .clearMap
    ld hl, $9906
    ld de, Title
    ld b, 8
.copyTitle
    ld a, [de]
    inc de
    ld [hli], a
    dec b
    jr nz, .copyTitle
    ld a, $e4
    ldh [$47], a
    ld a, $91
    ldh [$40], a
.forever
    jr .forever

MACRO row
    db \1, \1
ENDM
Tiles:
    ds 16, 0
; P
    row $00
    row $7c
    row $42
    row $42
    row $7c
    row $40
    row $40
    row $00
; O
    row $00
    row $3c
    row $42
    row $42
    row $42
    row $42
    row $3c
    row $00
; K
    row $00
    row $42
    row $44
    row $78
    row $48
    row $44
    row $42
    row $00
; E
    row $00
    row $7e
    row $40
    row $7c
    row $40
    row $40
    row $7e
    row $00
; S
    row $00
    row $3e
    row $40
    row $3c
    row $02
    row $42
    row $3c
    row $00
; L
    row $00
    row $40
    row $40
    row $40
    row $40
    row $40
    row $7e
    row $00
; T
    row $00
    row $7e
    row $18
    row $18
    row $18
    row $18
    row $18
    row $00
TilesEnd:
Title:
    db 1, 2, 3, 4, 5, 6, 2, 7
