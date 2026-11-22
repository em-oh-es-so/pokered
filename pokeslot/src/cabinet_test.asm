SECTION "Entry", ROM0[$100]
    nop
    jp Boot
    ds $150 - @, 0
SECTION "State", WRAM0
Buffer: ds 1
Phase: ds 1
Remaining: ds 1
OldA: ds 1
PressedA: ds 1
SECTION "Program", ROM0[$150]
Boot:
    di
    ld sp, $dfff
    xor a
    ldh [$ff], a
.wait
    ldh a, [$44]
    cp 144
    jr c, .wait
    xor a
    ldh [$40], a
    ldh [$42], a
    ldh [$43], a
    ldh [$26], a
    ld [Buffer], a
    ld [Phase], a
    ld [Remaining], a
    ld [OldA], a
    ld [PressedA], a
    ldh [$4f], a
    ld a, 1
    ld [$2000], a
    xor a
    ld [$3000], a
    ld hl, StaticTiles
    ld de, $8000
    ld bc, StaticTilesEnd-StaticTiles
    call Copy
    ld hl, BackgroundMap
    ld de, $9800
    ld bc, 1024
    call Copy
    ld a, 1
    ldh [$4f], a
    ld hl, $9800
    ld bc, 1024
.clearAttrs
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .clearAttrs
    call SetReelAttributes
    ld a, 2
    ld [$2000], a
    ld hl, FramesA
    ld de, $8000
    ld bc, 480
    call Copy
    xor a
    ldh [$4f], a
    call UpdateReelMap
    ld a, $80
    ldh [$68], a
    ld hl, Palette
    ld b, 8
.palette
    ld a, [hli]
    ldh [$69], a
    dec b
    jr nz, .palette
    ld a, $91
    ldh [$40], a
Main:
    call Frame
    call Input
    ld a, [Remaining]
    and a
    jr nz, .spin
    ld a, [PressedA]
    and a
    jr z, Main
    ld a, 36
    ld [Remaining], a
.spin
    call StreamStep
    ld hl, Remaining
    dec [hl]
    jr Main
StreamStep:
    ld a, [Phase]
    inc a
    cp 36
    jr c, .phase
    xor a
.phase
    ld [Phase], a
    ld e, a
    add a
    add e
    ld e, a
    ld d, 0
    ld hl, FrameSources
    add hl, de
    ld a, [hli]
    ld [$2000], a
    ld a, [hli]
    ldh [$52], a
    ld a, [hl]
    ldh [$51], a
    ld a, [Buffer]
    and a
    jr nz, .bufferZero
    ld a, 30
    ld [Buffer], a
    ld a, 1
    ldh [$53], a
    ld a, $e0
    ldh [$54], a
    jr .transfer
.bufferZero
    xor a
    ld [Buffer], a
    ldh [$53], a
    ldh [$54], a
.transfer
    ld a, 1
    ldh [$4f], a
    ld a, $9d
    ldh [$55], a
.waitDMA
    ldh a, [$55]
    bit 7, a
    jr z, .waitDMA
    xor a
    ldh [$4f], a
    call Frame
    call UpdateReelMap
    ret
Input:
    ld a, $10
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and 1
    ld b, a
    ld a, [OldA]
    cpl
    and b
    ld [PressedA], a
    ld a, b
    ld [OldA], a
    ld a, $30
    ldh [$00], a
    ret
Frame:
.out
    ldh a, [$44]
    cp 144
    jr nc, .out
.in
    ldh a, [$44]
    cp 144
    jr c, .in
    ret
Copy:
    ld a, [hli]
    ld [de], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, Copy
    ret
INCLUDE "build/stream/assets.inc"
