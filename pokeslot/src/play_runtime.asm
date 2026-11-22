InitPlay:
    ld hl, PlayStateStart
    ld bc, PlayStateEnd-PlayStateStart
.clear
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .clear
    ld a, $e8
    ld [Credits], a
    ld a, 3
    ld [Credits+1], a
    ld a, 1
    ld [Bet], a
    ld [RNG], a
    ld a, 5
    ld [LineIndex], a
    ld a, $a7
    ld [RNG+1], a
    ld a, $c1
    ld [RNG+2], a
    ld a, 9
    ld [RNG+3], a
    ret
SettingsInput:
    ld a, [PressedA]
    bit 6, a
    jr z, .down
    ld a, [Bet]
    cp 9
    jr nc, .down
    inc a
    ld [Bet], a
.down
    ld a, [PressedA]
    bit 7, a
    jr z, .right
    ld a, [Bet]
    cp 1
    jr z, .right
    dec a
    ld [Bet], a
.right
    ld a, [PressedA]
    bit 4, a
    jr z, .left
    ld a, [LineIndex]
    cp 5
    jr nc, .left
    inc a
    ld [LineIndex], a
.left
    ld a, [PressedA]
    bit 5, a
    ret z
    ld a, [LineIndex]
    and a
    ret z
    dec a
    ld [LineIndex], a
    ret
BeginSpin:
    xor a
    ld [Index], a
.stops
    call RandomStop
    ld c, a
    call GetIndex
    ld hl, Stops
    add hl, de
    ld [hl], c
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .stops
    call Evaluate
    ld [Status], a
    cp 1
    ret nz
    ld a, [Cost]
    ld c, a
    ld hl, Credits
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
    xor a
    ld [Payout], a
    ld [Payout+1], a
    ld [Index], a
    ld [PreviousLength], a
.length
    call GetIndex
    ld hl, Stops
    add hl, de
    ld a, [hl]
    ld c, a
    add a
    add c
    add a
    ld c, a
    ld hl, Phases
    add hl, de
    ld a, c
    sub [hl]
    jr nc, .positive
    add 36
.positive
    add 36
    ld c, a
    ld a, [PreviousLength]
    ld b, a
    ld a, c
.stagger
    cp b
    jr z, .longer
    jr nc, .store
.longer
    add 36
    jr .stagger
.store
    ld [PreviousLength], a
    ld hl, Remaining
    add hl, de
    ld [hl], a
    ld hl, Index
    inc [hl]
    ld a, [hl]
    cp 5
    jr c, .length
    ld a, 1
    ld [SpinActive], a
    ret
FinishSpin:
    ld hl, ResultCredits
    ld de, Credits
    ld bc, 4
    call Copy
    ld hl, Credits
    ld de, NumberWork
    ld bc, 4
    call Copy
    ; Recover gross payout from the same verified table without recharging.
    ; Original credits = final credits + cost - payout is not retained.
    ; Use the selected stops and bet directly to recover the table word.
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
    jr nc, .carry
    inc h
.carry
    dec b
    jr nz, .index
    add hl, hl
    ld de, $4000
    add hl, de
    ld a, [LineIndex]
    add 12
    ld [$2000], a
    ld a, [hli]
    ld d, [hl]
    ld e, a
    ld a, [Bet]
    ld b, a
    ld hl, 0
.multiply
    add hl, de
    dec b
    jr nz, .multiply
    ld a, l
    ld [Payout], a
    ld a, h
    ld [Payout+1], a
    xor a
    ld [SpinActive], a
    ret
RandomStop:
    call RandomByte
    cp 252
    jr nc, RandomStop
.mod
    cp 6
    ret c
    sub 6
    jr .mod
RandomByte:
    ld hl, RNG
    ld a, [hli]
    or [hl]
    inc hl
    or [hl]
    inc hl
    or [hl]
    jr nz, .nonzero
    ld a, 1
    ld [RNG], a
.nonzero
    call RandomCopy
    ld b, 13
.left13
    call ShiftLeftWork
    dec b
    jr nz, .left13
    call RandomXor
    call RandomCopy
    ld b, 17
.right17
    ld hl, RandomWork+3
    srl [hl]
    dec hl
    rr [hl]
    dec hl
    rr [hl]
    dec hl
    rr [hl]
    dec b
    jr nz, .right17
    call RandomXor
    call RandomCopy
    ld b, 5
.left5
    call ShiftLeftWork
    dec b
    jr nz, .left5
    call RandomXor
    ld a, [RNG+3]
    ret
RandomCopy:
    ld hl, RNG
    ld de, RandomWork
    ld bc, 4
    jp Copy
RandomXor:
    ld hl, RNG
    ld de, RandomWork
    ld b, 4
.loop
    ld a, [de]
    xor [hl]
    ld [hli], a
    inc de
    dec b
    jr nz, .loop
    ret
ShiftLeftWork:
    ld hl, RandomWork
    sla [hl]
    inc hl
    rl [hl]
    inc hl
    rl [hl]
    inc hl
    rl [hl]
    ret
ComputeCost:
    ld a, [LineIndex]
    ld e, a
    ld d, 0
    ld hl, LineCounts
    add hl, de
    ld c, [hl]
    ld a, [Bet]
    ld b, a
    xor a
.loop
    add c
    dec b
    jr nz, .loop
    ld [Cost], a
    ret
FormatByte:
    ld [NumberWork], a
    xor a
    ld [NumberWork+1], a
    ld [NumberWork+2], a
    ld [NumberWork+3], a
    jp FormatNumber
PrepareUI:
    call ComputeCost
    ld hl, Credits
    ld de, NumberWork
    ld bc, 4
    call Copy
    call FormatNumber
    ld hl, NumberText
    ld de, UI
    ld bc, 10
    call Copy
    ld hl, Payout
    ld de, NumberWork
    ld bc, 2
    call Copy
    xor a
    ld [NumberWork+2], a
    ld [NumberWork+3], a
    call FormatNumber
    ld hl, NumberText+5
    ld de, UI+10
    ld bc, 5
    call Copy
    ld a, [Bet]
    ld [UI+15], a
    ld a, [LineIndex]
    ld e, a
    ld d, 0
    ld hl, LineCounts
    add hl, de
    ld a, [hl]
    call FormatByte
    ld hl, NumberText+8
    ld de, UI+16
    ld bc, 2
    call Copy
    ld a, [Cost]
    call FormatByte
    ld hl, NumberText+7
    ld de, UI+18
    ld bc, 3
    jp Copy
OpenMenu:
    ld a, 1
    ld [MenuMode], a
    xor a
    ld [MenuPage], a
    call DrawMenu
.loop
    call Input
    call Frame
    ld a, [PressedA]
    bit 1, a
    jr nz, .exit
    bit 4, a
    jr nz, .next
    bit 5, a
    jr z, .loop
    ld a, [MenuPage]
    dec a
    jr .page
.next
    ld a, [MenuPage]
    inc a
.page
    and 3
    ld [MenuPage], a
    call DrawMenu
    jr .loop
.exit
    call Frame
    xor a
    ldh [$40], a
    ldh [$4f], a
    ld [MenuMode], a
    jp RestoreCabinet
DrawMenu:
    call Frame
    xor a
    ldh [$40], a
    ldh [$4f], a
    ld a, 18
    ld [$2000], a
    ld hl, MenuFont
    ld de, $8000
    ld bc, MenuFontEnd-MenuFont
    call Copy
    ld a, [MenuPage]
    add a
    add a
    add $44
    ld h, a
    ld l, 0
    ld de, $9800
    ld bc, 1024
    call Copy
    ld a, 1
    ldh [$4f], a
    ld hl, $9800
    ld bc, 1024
.attrs
    xor a
    ld [hli], a
    dec bc
    ld a, b
    or c
    jr nz, .attrs
    xor a
    ldh [$4f], a
    ld a, $91
    ldh [$40], a
    ret
