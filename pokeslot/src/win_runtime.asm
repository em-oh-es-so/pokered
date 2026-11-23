WinReset:
    ld a, [WinCount]
    and a
    ret z
    xor a
    ld [WinCount], a
    ld [WinPhase], a
    ld [WinReview], a
    ld a, 1
    ld [WinDirty], a
    ret
WinCollect:
    xor a
    ld [WinCount], a
    ld [WinCursor], a
    ld [WinPhase], a
    ld [WinReview], a
    ld [WinLine], a
    ld a, 1
    ld [WinDirty], a
    ld a, [Bet]
    ld [WinBet], a
    ld a, [LineIndex]
    ld e, a
    ld d, 0
    ld hl, LineCounts
    add hl, de
    ld a, [hl]
    ld [WinActive], a
.line
    ld a, [WinLine]
    ld c, a
    add a
    add a
    add c
    ld e, a
    ld d, 0
    ld hl, WinPaylines
    add hl, de
    ld a, [hli]
    ld c, a
    ld a, [Stops]
    add c
    cp 6
    jr c, .first
    sub 6
.first
    ld [WinSymbol], a
    ld a, 1
    ld [WinMatchWork], a
    ld [WinColumn], a
.column
    ld a, [hli]
    ld c, a
    push hl
    ld a, [WinColumn]
    ld e, a
    ld d, 0
    ld hl, Stops
    add hl, de
    ld a, [hl]
    add c
    cp 6
    jr c, .symbol
    sub 6
.symbol
    ld c, a
    ld a, [WinSymbol]
    cp c
    pop hl
    jr nz, .matched
    ld a, [WinMatchWork]
    inc a
    ld [WinMatchWork], a
    ld a, [WinColumn]
    inc a
    ld [WinColumn], a
    cp 5
    jr c, .column
.matched
    ld a, [WinMatchWork]
    cp 3
    jp c, .next
    ld a, [WinSymbol]
    ld c, a
    add a
    add c
    add a
    ld e, a
    ld a, [WinMatchWork]
    sub 3
    add a
    add e
    ld e, a
    ld d, 0
    ld hl, WinPaytable
    add hl, de
    ld a, [hli]
    ld d, [hl]
    ld e, a
    ld a, [WinBet]
    ld b, a
    ld hl, 0
.amount
    add hl, de
    dec b
    jr nz, .amount
    push hl
    ld a, [WinCount]
    add a
    add a
    ld e, a
    ld d, 0
    ld hl, WinList
    add hl, de
    pop de
    ld a, [WinLine]
    ld [hli], a
    ld a, [WinMatchWork]
    ld [hli], a
    ld a, e
    ld [hli], a
    ld [hl], d
    ld hl, WinCount
    inc [hl]
.next
    ld a, [WinLine]
    inc a
    ld [WinLine], a
    ld b, a
    ld a, [WinActive]
    cp b
    jp nz, .line
    ld a, [WinCount]
    and a
    ret z
    ld a, 1
    ld [WinPhase], a
    ld a, 30
    ld [WinTimer], a
    jp WinSelect
WinSelect:
    ld a, [WinCursor]
    add a
    add a
    ld e, a
    ld d, 0
    ld hl, WinList
    add hl, de
    ld a, [hli]
    ld [WinLine], a
    ld a, [hli]
    ld [WinMatched], a
    ld a, [hli]
    ld [WinAmount], a
    ld a, [hl]
    ld [WinAmount+1], a
    ld a, [WinLine]
    ld c, a
    add a
    add a
    add c
    ld e, a
    ld d, 0
    ld hl, WinPaylines
    add hl, de
    ld de, WinRows
    ld bc, 5
    call Copy
    ld hl, WinFooterTemplate
    ld de, WinFooter
    ld bc, 20
    call Copy
    ld a, [WinReview]
    and a
    jr z, .numbers
    ld hl, WinViewWord
    ld de, WinFooter
    ld bc, 4
    call Copy
.numbers
    ld a, [WinLine]
    inc a
    call FormatByte
    ld a, [NumberText+8]
    cp 10
    jr nz, .lineDigits
    xor a
    ld [NumberText+8], a
.lineDigits
    ld hl, NumberText+8
    ld de, WinFooter+5
    ld b, 2
    call WinDigits
    ld hl, WinAmount
    ld de, NumberWork
    ld bc, 2
    call Copy
    xor a
    ld [NumberWork+2], a
    ld [NumberWork+3], a
    call FormatNumber
    ld hl, NumberText+5
    ld de, WinFooter+12
    ld b, 5
    jp WinDigits
WinDigits:
    ld a, [hli]
    push hl
    ld c, a
    ld hl, DigitTiles
    ld a, l
    add c
    ld l, a
    jr nc, .lookup
    inc h
.lookup
    ld a, [hl]
    pop hl
    ld [de], a
    inc de
    dec b
    jr nz, WinDigits
    ret
WinNext:
    ld a, [WinCursor]
    inc a
    ld b, a
    ld a, [WinCount]
    cp b
    ld a, b
    jr nz, .store
    xor a
.store
    ld [WinCursor], a
    jp WinSelect
WinTick:
IF DEF(WIN_TESTS)
    ld a, [WinTestCommand]
    cp 1
    jr nz, .notTest
    call WinCollect
    xor a
    ld [WinTestCommand], a
.notTest
ENDC
    ld a, [WinCount]
    and a
    ret z
    ld a, [WinReview]
    and a
    jr z, .pulse
    ld a, [WinPhase]
    and a
    ret nz
    ld a, 1
    ld [WinPhase], a
    ld [WinDirty], a
    ret
.pulse
    ld hl, WinTimer
    dec [hl]
    ret nz
    ld [hl], 30
    ld a, [WinPhase]
    xor 1
    ld [WinPhase], a
    and a
    call nz, WinNext
    ld a, 1
    ld [WinDirty], a
    ret
SettingsInput:
    call WinControls
    ld a, [WinReview]
    and a
    ret nz
    jp NormalSettingsInput
WinControls:
    ld a, [WinCount]
    and a
    ret z
    ld a, [PressedA]
    bit 3, a
    jr z, .browse
    ld a, [WinReview]
    xor 1
    ld [WinReview], a
    ld a, 1
    ld [WinPhase], a
    ld [WinDirty], a
    ld a, 30
    ld [WinTimer], a
    call WinSelect
.browse
    ld a, [WinReview]
    and a
    ret z
    ld a, [PressedA]
    bit 4, a
    jr nz, .next
    bit 5, a
    ret z
    ld a, [WinCursor]
    and a
    jr nz, .previous
    ld a, [WinCount]
.previous
    dec a
    ld [WinCursor], a
    call WinSelect
    jr .dirty
.next
    call WinNext
.dirty
    ld a, 1
    ld [WinDirty], a
    ret
OpenMenu:
    xor a
    ld [WinPhase], a
    ld [WinDirty], a
    ld a, 30
    ld [WinTimer], a
    jp NormalOpenMenu
WinRender:
    xor a
    ld [WinDirty], a
    call TransferAll
    xor a
    ldh [$4f], a
    call Frame
    call SwapAll
    jp PaintAll
GetSource:
    ld a, [WinPhase]
    and a
    jp z, NormalGetSource
    ld a, [Index]
    ld b, a
    ld a, [WinMatched]
    cp b
    jp z, NormalGetSource
    jp c, NormalGetSource
    call GetIndex
    ld hl, Phases
    add hl, de
    ld a, [hl]
    ld c, 0
.divide
    cp 6
    jr c, .stop
    sub 6
    inc c
    jr .divide
.stop
    ld a, c
    add a
    add c
    ld c, a
    ld hl, WinRows
    add hl, de
    ld a, [hl]
    add c
    ld [WinFrameNumber], a
    call GetSize
    ld d, b
    ld e, c
    ld hl, 0
    ld a, [WinFrameNumber]
    ld b, a
    and a
    jr z, .address
.multiply
    add hl, de
    dec b
    jr nz, .multiply
.address
    ld de, $4000
    add hl, de
    ld a, [Index]
    add 19
    ld [$2000], a
    ret
PaintFooterBase:
    xor a
    ldh [$4f], a
    ld a, 1
    ld [$2000], a
    ld hl, BackgroundMap+17*32
    ld de, $9800+17*32
    ld bc, 20
    jp Copy
PaintWinFooter:
    ld a, [WinCount]
    and a
    ret z
    ld hl, WinFooter
    ld de, $9800+17*32
    ld bc, 20
    jp Copy
