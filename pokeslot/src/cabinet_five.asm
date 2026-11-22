SECTION "Entry", ROM0[$100]
    nop
    jp Boot
    ds $150 - @, 0
SECTION "State", WRAM0
StateStart:
Index: ds 1
OldA: ds 1
PressedA: ds 1
Length: ds 1
Visible: ds 5
Hidden: ds 5
Phases: ds 5
Remaining: ds 5
StateEnd:
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
    ldh [$4f], a
    ld hl, StateStart
    ld b, StateEnd-StateStart
.clear
    ld [hli], a
    dec b
    jr nz, .clear
    ld a, $30
    ldh [$00], a
    ld a, 1
    ldh [$4d], a
    stop
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
    call SetAttributes
    ld hl, InitialVisible
    ld de, Visible
    ld bc, 5
    call Copy
    ld hl, InitialHidden
    ld de, Hidden
    ld bc, 5
    call Copy
    ld hl, InitialPhases
    ld de, Phases
    ld bc, 5
    call Copy
    xor a
    ld [Index], a
.initialReel
    call GetBank
    ldh [$4f], a
    call GetIndex
    ld hl, Visible
    add hl, de
    ld a, [hl]
    call TileAddress
    push de
    call GetSize
    push bc
    call GetSource
    pop bc
    pop de
    call Copy
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .initialReel
    xor a
    ldh [$4f], a
    call PaintAll
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
    call Input
    call AnyMoving
    jr nz, .animate
    ld a, [PressedA]
    and a
    jr nz, .begin
    call Frame
    jr Main
.begin
    ld hl, SpinLengths
    ld de, Remaining
    ld bc, 5
    call Copy
.animate
    call Advance
    call TransferAll
    xor a
    ldh [$4f], a
    call Frame
    call SwapAll
    call PaintAll
    jp Main
AnyMoving:
    ld hl, Remaining
    ld b, 5
    xor a
.loop
    or [hl]
    inc hl
    dec b
    jr nz, .loop
    and a
    ret
Advance:
    xor a
    ld [Index], a
.loop
    call GetIndex
    ld hl, Remaining
    add hl, de
    ld a, [hl]
    and a
    jr z, .next
    dec [hl]
    ld hl, Phases
    add hl, de
    ld a, [hl]
    inc a
    cp 36
    jr c, .store
    xor a
.store
    ld [hl], a
.next
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .loop
    ret
TransferAll:
    xor a
    ld [Index], a
.loop
    call GetBank
    ldh [$4f], a
    call GetIndex
    ld hl, Hidden
    add hl, de
    ld a, [hl]
    call TileAddress
    ld a, d
    and $1f
    ldh [$53], a
    ld a, e
    ldh [$54], a
    call GetIndex
    ld hl, TileCounts
    add hl, de
    ld a, [hl]
    dec a
    or $80
    ld [Length], a
    call GetSource
    ld a, h
    ldh [$51], a
    ld a, l
    ldh [$52], a
.notHBlank
    ldh a, [$41]
    and 3
    jr z, .notHBlank
    ld a, [Length]
    ldh [$55], a
.waitDMA
    ldh a, [$55]
    bit 7, a
    jr z, .waitDMA
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .loop
    ret
SwapAll:
    ld de, 0
.loop
    ld hl, Visible
    add hl, de
    ld b, [hl]
    ld hl, Hidden
    add hl, de
    ld c, [hl]
    ld [hl], b
    ld hl, Visible
    add hl, de
    ld [hl], c
    inc e
    ld a, e
    cp 5
    jr c, .loop
    ret
PaintAll:
    xor a
    ld [Index], a
.loop
    ld a, [Index]
    add a
    ld e, a
    ld d, 0
    ld hl, PaintTable
    add hl, de
    ld a, [hli]
    ld h, [hl]
    ld l, a
    call CallHL
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .loop
    ret
CallHL:
    jp hl
GetIndex:
    ld a, [Index]
    ld e, a
    ld d, 0
    ret
GetBank:
    call GetIndex
    ld hl, VRAMBanks
    add hl, de
    ld a, [hl]
    ret
GetSize:
    ld a, [Index]
    add a
    ld e, a
    ld d, 0
    ld hl, FrameSizes
    add hl, de
    ld a, [hli]
    ld b, [hl]
    ld c, a
    ret
GetSource:
    call GetIndex
    ld hl, Phases
    add hl, de
    ld c, [hl]
    ld a, [Index]
    add a
    ld e, a
    ld hl, FrameTables
    add hl, de
    ld a, [hli]
    ld h, [hl]
    ld l, a
    ld a, c
    add a
    add c
    ld e, a
    ld d, 0
    add hl, de
    ld a, [hli]
    ld [$2000], a
    ld a, [hli]
    ld h, [hl]
    ld l, a
    ret
TileAddress:
    swap a
    ld b, a
    and $f0
    ld e, a
    ld a, b
    and $0f
    add $80
    ld d, a
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
INCLUDE "build/five/assets.inc"
