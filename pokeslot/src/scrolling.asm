INCLUDE "build/assets.inc"
SECTION "Entry", ROM0[$100]
    nop
    jp Boot
    ds $150 - @, 0
SECTION "State", WRAM0
StateStart:
Mode: ds 1
Coins: ds 1
Bet: ds 1
OldKeys: ds 1
Pressed: ds 1
Timer: ds 1
Index: ds 1
Moving: ds 1
Phases: ds 5
StateEnd:
SECTION "Code", ROM0[$150]
Boot:
    di
    ld sp, $dfff
    xor a
    ldh [$ff], a
    call LCDOff
    xor a
    ldh [$42], a
    ldh [$43], a
    ldh [$26], a
    ld hl, StateStart
    ld b, StateEnd-StateStart
.clear
    ld [hli], a
    dec b
    jr nz, .clear
    ld a, 200
    ld [Coins], a
    ld a, 1
    ld [Bet], a
    ld hl, InitialPhases
    ld de, Phases
    ld bc, 5
    call Copy
    ld hl, Tiles
    ld de, $8000
    ld bc, TilesEnd-Tiles
    call Copy
    ld hl, TitleMap
    call LoadMap
    ld a, $e4
    ldh [$47], a
    ld a, $91
    ldh [$40], a
Main:
    call Frame
    call Input
    ld a, [Mode]
    and a
    jp z, TitleInput
    cp 2
    jp z, SpinFrame
    call IdleInput
    call Display
    jp Main
TitleInput:
    ld a, [Pressed]
    bit 3, a
    jp z, Main
    call LCDOff
    ld hl, MachineMap
    call LoadMap
    ld a, 1
    ld [Mode], a
    ld a, $91
    ldh [$40], a
    jp Main
IdleInput:
    ld a, [Pressed]
    bit 2, a
    jr z, .up
    ld a, 200
    ld [Coins], a
    ld a, 1
    ld [Bet], a
.up
    ld a, [Pressed]
    bit 6, a
    jr z, .down
    ld a, [Bet]
    cp 9
    jr nc, .down
    inc a
    ld [Bet], a
.down
    ld a, [Pressed]
    bit 7, a
    jr z, .spin
    ld a, [Bet]
    cp 1
    jr z, .spin
    dec a
    ld [Bet], a
.spin
    ld a, [Pressed]
    bit 0, a
    ret z
    ld a, [Bet]
    ld b, a
    ld a, [Coins]
    cp b
    ret c
    sub b
    ld [Coins], a
    ldh a, [$04]
    and 31
    add 120
    ld [Timer], a
    ld a, 2
    ld [Mode], a
    ret
SpinFrame:
    ld a, [Timer]
    and a
    jr z, .settle
    dec a
    ld [Timer], a
.settle
    xor a
    ld [Index], a
    ld [Moving], a
.loop
    ld a, [Index]
    ld e, a
    ld d, 0
    ld hl, Phases
    add hl, de
    ld c, [hl]
    ld hl, Stops
    add hl, de
    ld a, [Timer]
    cp [hl]
    jr nc, .advance
    ld a, c
.mod
    cp 6
    jr c, .remainder
    sub 6
    jr .mod
.remainder
    and a
    jr z, .next
.advance
    ld a, 1
    ld [Moving], a
    ld a, c
    inc a
    cp 36
    jr c, .store
    xor a
.store
    ld hl, Phases
    add hl, de
    ld [hl], a
.next
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .loop
    call Render
    ld a, [Timer]
    and a
    jp nz, Main
    ld a, [Moving]
    and a
    jp nz, Main
    ld a, 1
    ld [Mode], a
    jp Main
Render:
    xor a
    ld [Index], a
.column
    ld a, [Index]
    ld e, a
    ld d, 0
    ld hl, Phases
    add hl, de
    ld a, [hl]
    add a
    ld e, a
    ld hl, FramePointers
    add hl, de
    ld a, [hli]
    ld h, [hl]
    ld l, a
    push hl
    ld a, [Index]
    add a
    ld e, a
    ld hl, Destinations
    add hl, de
    ld a, [hli]
    ld d, [hl]
    ld e, a
    pop hl
    ld c, 9
.row
    ld a, [hli]
    call WriteTile
    inc de
    ld a, [hli]
    call WriteTile
    inc de
    ld a, [hli]
    call WriteTile
    ld a, e
    add 30
    ld e, a
    jr nc, .noCarry
    inc d
.noCarry
    dec c
    jr nz, .row
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .column
    ret
WriteTile:
    ld b, a
.wait
    ldh a, [$41]
    and 2
    jr nz, .wait
    ld a, b
    ld [de], a
    ret
Display:
    ld a, [Coins]
    ld c, DIGIT_ZERO
.hundreds
    cp 100
    jr c, .hDone
    sub 100
    inc c
    jr .hundreds
.hDone
    push af
    ld de, $9867
    ld a, c
    call WriteTile
    pop af
    ld c, DIGIT_ZERO
.tens
    cp 10
    jr c, .tDone
    sub 10
    inc c
    jr .tens
.tDone
    push af
    inc de
    ld a, c
    call WriteTile
    pop af
    inc de
    add DIGIT_ZERO
    call WriteTile
    ld de, $986f
    ld a, [Bet]
    add DIGIT_ZERO
    jp WriteTile
Input:
    ld a, $10
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and $0f
    ld b, a
    ld a, $20
    ldh [$00], a
    ldh a, [$00]
    ldh a, [$00]
    ldh a, [$00]
    cpl
    and $0f
    swap a
    or b
    ld b, a
    ld a, [OldKeys]
    cpl
    and b
    ld [Pressed], a
    ld a, b
    ld [OldKeys], a
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
LCDOff:
    ldh a, [$40]
    bit 7, a
    ret z
.wait
    ldh a, [$44]
    cp 144
    jr c, .wait
    xor a
    ldh [$40], a
    ret
LoadMap:
    ld de, $9800
    ld bc, 1024
Copy:
    ld a, [hli]
    ld [de], a
    inc de
    dec bc
    ld a, b
    or c
    jr nz, Copy
    ret
