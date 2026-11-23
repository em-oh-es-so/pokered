SECTION "Cabinet cry driver", ROM0
CabinetCryInit:
    ld hl, CabinetCryStateStart
    ld b, CabinetCryStateEnd-CabinetCryStateStart
    xor a
.clear
    ld [hli], a
    dec b
    jr nz, .clear
    ld a, 2
    ld [CabinetCryMode], a
    ret
CabinetCryAssess:
    xor a
    ld [CabinetCryEligible], a
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
    ld de, $4000
    add hl, de
    ld a, [LineIndex]
    add 25
    ld [$2000], a
    ld a, [hl]
    ld [CabinetCryEncoded], a
    and 7
    ld [CabinetCrySelected], a
    ld a, 1
    ld [$2000], a
    ld a, [CabinetCrySelected]
    cp 6
    ret nc
    ld a, [CabinetCryMode]
    and a
    ret z
    cp 1
    jr z, .eligible
    cp 2
    ret nz
    ld a, [CabinetCryEncoded]
    bit 3, a
    ret z
.eligible
    ld a, 1
    ld [CabinetCryEligible], a
    ret
CabinetRequestCry:
    push af
    push bc
    push de
    push hl
    call CabinetCryAssess
    ld a, [CabinetCryEligible]
    and a
    jr z, .exit
    di
    ld a, [CabinetCryCount]
    cp 8
    jr nc, .overflow
    ld a, [CabinetCryTail]
    ld e, a
    ld d, 0
    ld hl, CabinetCryQueue
    add hl, de
    ld a, [CabinetCrySelected]
    ld [hl], a
    ld a, e
    inc a
    and 7
    ld [CabinetCryTail], a
    ld hl, CabinetCryCount
    inc [hl]
    ld hl, CabinetCryQueued
    inc [hl]
    jr nz, .enable
    inc hl
    inc [hl]
    jr .enable
.overflow
    ld a, 1
    ld [CabinetCryOverflow], a
.enable
    ei
.exit
    pop hl
    pop de
    pop bc
    pop af
    ret
CabinetCryBusy:
    ld hl, wChannelSoundIDs+4
    ld b, 4
.loop
    ld a, [hli]
    cp CRY_SFX_START
    jr nc, .busy
    dec b
    jr nz, .loop
    xor a
    ret
.busy
    ld a, 1
    and a
    ret
CabinetCryService:
    ld a, [CabinetCryActive]
    and a
    jr z, .pending
    call CabinetCryBusy
    ret nz
    xor a
    ld [CabinetCryActive], a
    ld [wFrequencyModifier], a
    ld [wTempoModifier], a
    ld a, [CabinetCrySavedVolume]
    ldh [$FF24], a
    ld hl, CabinetCryCompleted
    inc [hl]
    jr nz, .pending
    inc hl
    inc [hl]
.pending
    ld a, [CabinetCryCount]
    and a
    jp z, .allowEffects
    ld a, [CabinetEffectCount]
    and a
    jp nz, .allowEffects
    call CabinetCryBusy
    jp nz, .allowEffects
.start
    ld a, [CabinetCryCount]
    dec a
    ld [CabinetCryCount], a
    ld a, [CabinetCryHead]
    ld e, a
    ld d, 0
    ld hl, CabinetCryQueue
    add hl, de
    ld c, [hl]
    ld a, e
    inc a
    and 7
    ld [CabinetCryHead], a
    ld a, c
    ld [CabinetCryLastSpecies], a
    add a
    add c
    ld e, a
    ld hl, CabinetCryPresets
    add hl, de
    ld a, [hli]
    push af
    ld a, [hli]
    ld [CabinetCryLastPitch], a
    ld [wFrequencyModifier], a
    ld a, [hl]
    ld [CabinetCryLastDuration], a
    ld [wTempoModifier], a
    ldh a, [$FF24]
    ld [CabinetCrySavedVolume], a
    ld [wSavedVolume], a
    ld a, $33
    ldh [$FF24], a
    ld a, 1
    ld [CabinetCryActive], a
    pop af
    push af
    call $a003
    pop af
    ld c, a
    ld hl, wChannelSoundIDs+4
    ld b, 4
.check
    ld a, [hli]
    cp c
    jr z, .present
    dec b
    jr nz, .check
    ld a, 1
    ld [CabinetCryPresenceFault], a
.present
    ld hl, CabinetCryPlayed
    inc [hl]
    jr nz, .blocked
    inc hl
    inc [hl]
.blocked
    ld a, 1
    and a
    ret
.allowEffects
    xor a
    ret
IF DEF(WIN_TESTS)
CabinetCryTestCommand:
    ld a, [WinTestCommand]
    cp 2
    jr z, .assess
    cp 3
    ret nz
    call WinCollect
    call CabinetPayoutEffect
    call CabinetRequestCry
    jr .done
.assess
    call CabinetCryAssess
.done
    xor a
    ld [WinTestCommand], a
    ret
ENDC
