import pygame
import os

pygame.init()

upscale = 15
display = [[0 for _ in range(64)] for _ in range(32)]
running = advance_pc = True
rom_finished = False
pygame.display.set_caption("Chip-8 emulator")

# Set up specs
memory = bytearray(4096)
V = [0] * 16
stack = [0] * 16
keys = [False] * 16
pc = 0x200
delay_timer = sound_timer = keyindex = hold_x = sp = I = 0
wait_key = False
clock = pygame.time.Clock()
last_timer_update = pygame.time.get_ticks()
beep = pygame.mixer.Sound("beep.wav")

keymap = {
    pygame.K_1: 0x1, pygame.K_2: 0x2, pygame.K_3: 0x3, pygame.K_4: 0xC,
    pygame.K_q: 0x4, pygame.K_w: 0x5, pygame.K_e: 0x6, pygame.K_r: 0xD,
    pygame.K_a: 0x7, pygame.K_s: 0x8, pygame.K_d: 0x9, pygame.K_f: 0xE,
    pygame.K_z: 0xA, pygame.K_x: 0x0, pygame.K_c: 0xB, pygame.K_v: 0xF
}

# User select rom from a list
# (Requires some improvements)
files = [f for f in os.listdir() if os.path.isfile(f)]
k = 1
for i in files:
    if not i.endswith(".ch8"):
        files.remove(i)
for i in files:
    print(k,": ", i, sep="")
    k += 1
selected_rom = int(input("Choose a ROM: "))

# Loading up the rom
def load_rom(path):
    with open(path, 'rb') as f:
        rom = f.read()
    for i in range(len(rom)):
        memory[0x200 + i] = rom[i]
    return len(rom)

rom_size = load_rom(files[selected_rom-1])
rom_end = 0x200 + rom_size
screen = pygame.display.set_mode((64 * upscale, 32 * upscale))

# CPU cycle
while running:
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Keyboard events
        # Keydown
        if event.type == pygame.KEYDOWN:
            if event.key in keymap:
                keyindex = keymap[event.key]
                keys[keyindex] = True
                input_set = True
        # Keyup
        elif event.type == pygame.KEYUP:
            if event.key in keymap:
                keyindex = keymap[event.key]
                keys[keyindex] = False
                input_set = False

                if wait_key:
                    wait_key = False
                    V[hold_x] = keyindex
                    pc += 2

    if pc + 1 < rom_end and rom_finished == False:
        opcode = (memory[pc] << 8 | memory[pc + 1])
        X = (opcode & 0x0F00) >> 8
        Y = (opcode & 0x00F0) >> 4

        # Instructions
        match(opcode & 0xF000):
            case 0x0000:
                if (opcode & 0x00FF) == 0x00E0:
                    for x in range(64):
                        for y in range(32):
                            display[y][x] = 0
                    screen.fill((0,0,0))
                elif (opcode & 0x00FF) == 0x00EE:
                    advance_pc = False
                    sp -= 1
                    pc = stack[sp]
            case 0x1000:
                advance_pc = False
                pc = (opcode & 0x0FFF)
            case 0x2000:
                advance_pc = False
                stack[sp] = pc + 2
                sp += 1
                pc = (opcode & 0x0FFF)
            case 0x3000:
                if V[X] == opcode & 0x00FF:
                    pc += 2
                else:
                    pass
            case 0x4000:
                if V[X] != opcode & 0x00FF:
                    pc += 2
                else:
                    pass
            case 0x5000:
                if V[X] == V[Y]:
                    pc += 2
                else:
                    pass
            case 0x6000:
                V[X] = opcode & 0x00FF
            case 0x7000:
                V[X] = V[X] + (opcode & 0x00FF) & 0xFF
            case 0x8000:
                # Cases for 8XY0 - 8XYE
                match(opcode & 0x000F):
                    case 0x0:
                        V[X] = V[Y]
                    case 0x1:
                        V[X] = V[Y] | V[X]
                    case 0x2:
                        V[X] = V[Y] & V[X]
                    case 0x3:
                        V[X] = V[Y] ^ V[X]
                    case 0x4:
                        if (V[X] + V[Y]) > 255:
                            V[15] = 1
                        else:
                            V[15] = 0
                        V[X] = (V[X] + V[Y]) & 0xFF
                    case 0x5:
                        if (V[X] - V[Y]) >= 0:
                            V[15] = 1
                        else:
                            V[15] = 0
                        V[X] = (V[X] - V[Y]) & 0xFF
                    case 0x6:
                        p = V[X]
                        V[X] = (V[X] >> 1) & 0xFF
                        V[15] = (p & 0x80) >> 7
                    case 0x7:
                        if (V[Y] - V[X]) < 0:
                            V[15] = 0
                        else:
                            V[15] = 1
                        V[X] = V[Y] - V[X] & 0xFF
                    case 0xE:
                        p = V[X]
                        V[X] = (V[X] << 1) & 0xFF
                        if (p & 0x80) >> 7 == 1:
                            V[15] = 1
                        else:
                            V[15] = 0
            case 0x9000:
                if V[X] != V[Y]:
                    pc += 2
                else:
                    pass
            case 0xA000:
                I = (opcode & 0x0FFF)
            case 0xB000:
                advance_pc = False
                pc = (opcode & 0x0FFF) + V[0]
            case 0xD000:
                X = V[(opcode & 0x0F00) >> 8]
                Y = V[(opcode & 0x00F0) >> 4]
                V[15] = 0
                # Loading sprite data from memory
                for i in range(opcode & 0x000F):
                    sprite_byte = memory[I + i]
                    for bit in range(8):
                        sprite_bit = (sprite_byte >> (7 - bit)) & 1
                        xc = (X + bit) % 64
                        yc = (Y + i) % 32
                        if sprite_bit == 1:
                            if display[yc][xc] == 1:
                                V[15] = 1
                            display[(yc)][(xc)] ^= sprite_bit
                screen.fill((0,0,0))
                # Drawing pixels to the screen
                for x in range(64):
                    for y in range(32):
                        if display[y][x] == 1:
                            pygame.draw.rect(screen, (255, 255, 255), (x * upscale, y * upscale, upscale, upscale))
                            
            case 0xE000:
                match(opcode & 0x00FF):
                    case 0x9E:
                        if keys[V[X]] and wait_key == False:
                            pc += 2
                    case 0xA1:
                        if keys[V[X]] == False and wait_key == False:
                            pc += 2
            case 0xF000:
                # Cases for FX07 - FX65
                tempI = I
                match(opcode & 0x00FF):
                    case 0x0A:
                        wait_key = True
                        hold_x = X
                        advance_pc = False
                    case 0x07:
                        V[X] = delay_timer
                    case 0x15:
                        delay_timer = V[X]
                    case 0x18:
                        sound_timer = V[X]
                    case 0x1E:
                        I = I + V[X]
                    case 0x65:
                        for i in range(X + 1):
                            V[i] = memory[tempI]
                            tempI = tempI + 1
                    case 0x55:
                        for i in range(X + 1):
                            memory[tempI] = V[i]
                            tempI = tempI + 1
                    case 0x33:
                        memory[I] = V[X] // 100
                        memory[I+1] = (V[X] // 10) % 10
                        memory[I+2] = V[X] % 10
        if advance_pc:
            pc += 2
    else:
        rom_finished = True

    # Updating delay and sound timers
    if current_time - last_timer_update >= 1000/60:
        if delay_timer > 0:
            delay_timer -= 1
        if sound_timer > 0:
            sound_timer -= 1
            beep.play(1)
        last_timer_update = current_time
    
    advance_pc = True
    pygame.display.update()