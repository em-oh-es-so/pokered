SECTION "Entry", ROM0[$100]
    nop
    jp Boot
    ds $150 - @, 0
SECTION "Mailbox", WRAM0[$c000]
Command: ds 1
Status: ds 1
Credits: ds 4
Stops: ds 5
Bet: ds 1
LineIndex: ds 1
ResultCredits: ds 4
Payout: ds 2
Cost: ds 1
SECTION "Ready Flag", WRAM0[$c0ff]
Ready: ds 1
SECTION "Code", ROM0[$150]
Boot:
    di
    ld sp, $dfff
    xor a
    ldh [$ff], a
    ld [Ready], a
.wait
    ldh a, [$44]
    cp 144
    jr c, .wait
    xor a
    ldh [$40], a
    ld [$3000], a
    ld [Command], a
    ld [Status], a
    ld a, $a5
    ld [Ready], a
Main:
    ld a, [Command]
    cp 1
    jr nz, Main
    xor a
    ld [Command], a
    call Evaluate
    ld [Status], a
    jr Main
Evaluate:
    ld hl, Credits
    ld de, ResultCredits
    ld bc, 4
    call Copy
    xor a
    ld [Payout], a
    ld [Payout + 1], a
    ld [Cost], a
    ld a, [Bet]
    and a
    jp z, Invalid
    cp 10
    jp nc, Invalid
    ld a, [LineIndex]
    cp 6
    jp nc, Invalid
    ld hl, Stops
    ld b, 5
.validateStops
    ld a, [hli]
    cp 6
    jp nc, Invalid
    dec b
    jr nz, .validateStops
    ld a, [LineIndex]
    ld e, a
    ld d, 0
    ld hl, LineCounts
    add hl, de
    ld c, [hl]
    ld a, [Bet]
    ld b, a
    xor a
.cost
    add c
    dec b
    jr nz, .cost
    ld [Cost], a
    ld c, a
    ld a, [Credits + 1]
    ld b, a
    ld a, [Credits + 2]
    or b
    ld b, a
    ld a, [Credits + 3]
    or b
    jr nz, .funded
    ld a, [Credits]
    cp c
    jp c, Insufficient
.funded
    ld hl, 0
    ld de, Stops
    ld b, 5
.index
    push de
    ld d, h
    ld e, l
    add hl, hl
    add hl, de
    add hl, hl
    pop de
    ld a, [de]
    inc de
    add l
    ld l, a
    jr nc, .noCarry
    inc h
.noCarry
    dec b
    jr nz, .index
    add hl, hl
    ld de, $4000
    add hl, de
    ld a, [LineIndex]
    inc a
    ld [$2000], a
    ld a, [hli]
    ld d, [hl]
    ld e, a
    ld hl, 0
    ld a, [Bet]
    ld b, a
.multiply
    add hl, de
    dec b
    jr nz, .multiply
    ld a, l
    ld [Payout], a
    ld a, h
    ld [Payout + 1], a
    ld a, [Cost]
    ld c, a
    ld hl, ResultCredits
    ld a, [hl]
    sub c
    ld [hli], a
    ld a, [hl]
    sbc 0
    ld [hli], a
    ld a, [hl]
    sbc 0
    ld [hli], a
    ld a, [hl]
    sbc 0
    ld [hl], a
    ld a, [Payout]
    ld c, a
    ld hl, ResultCredits
    ld a, [hl]
    add c
    ld [hli], a
    ld a, [Payout + 1]
    ld c, a
    ld a, [hl]
    adc c
    ld [hli], a
    ld a, [hl]
    adc 0
    ld [hli], a
    ld a, [hl]
    adc 0
    ld [hl], a
    jp c, Overflow
    ld a, 1
    ret
Invalid:
    ld a, 2
    ret
Insufficient:
    ld a, 3
    ret
Overflow:
    ld hl, Credits
    ld de, ResultCredits
    ld bc, 4
    call Copy
    ld a, 4
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
INCLUDE "build/accounting/tables.inc"
