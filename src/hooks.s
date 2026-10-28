# Entry points the patched game code jumps or calls into (USA CUSA13795 1.21, ELF addresses).
# Game addresses are symbols set by build.py; all references are RIP-relative.

    .intel_syntax noprefix
    .text

# Hooks placed in the middle of game code: keep every register a C call may change (also the
# vector registers) and align the stack, whatever its alignment was.
.macro SAVE
    push rax
    push rcx
    push rdx
    push rsi
    push rdi
    push r8
    push r9
    push r10
    push r11
    push rbx
    mov rbx, rsp
    and rsp, -16
    sub rsp, 256
    .irp n, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
    movdqu [rsp + \n * 16], xmm\n
    .endr
.endm

.macro RESTORE
    .irp n, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
    movdqu xmm\n, [rsp + \n * 16]
    .endr
    mov rsp, rbx
    pop rbx
    pop r11
    pop r10
    pop r9
    pop r8
    pop rdi
    pop rsi
    pop rdx
    pop rcx
    pop rax
.endm

# Replaces "call send_event(target, event)" at 0x9b3e88 when a ghost menu entry is set up.
# The entry's behavior object is at [rbp-0xb0] in that function.
    .globl hook_entry_setup
hook_entry_setup:
    mov rdx, [rbp - 0xb0]
    jmp gs_send_entry_setup

# Replaces "cmp dword [r13+0x18], 8; jne exit" at 0x9b3a53 (a button on a ghost menu entry).
# r13 = input event (+0x18 signal), r15 = entry behavior (+0x4d: it is your own ghost).
    .globl hook_button
hook_button:
    cmp dword ptr [r13 + 0x18], 8           # Select: the game's own code
    je game_button_select
    SAVE                                    # other buttons: gs_entry_button(signal, own ghost)
    mov edi, [r13 + 0x18]
    movzx esi, byte ptr [r15 + 0x4d]
    call gs_entry_button
    RESTORE
    jmp game_button_exit                    # as the game does for every other button

# Called from 0xf9b298 at race start (r15 = ghost manager), in place of "cmp byte [r15+0x48], 0".
    .globl hook_take_chosen
hook_take_chosen:
    SAVE
    mov rdi, r15
    call gs_take_chosen
    RESTORE
    cmp byte ptr [r15 + 0x48], 0            # the replaced instruction; ret keeps the flags
    ret

# Called from 0xf9b329 at race start (r15 = ghost manager), in place of "mov al, [0x2a92868]".
    .globl hook_add_chosen
hook_add_chosen:
    SAVE
    mov rdi, r15
    call gs_add_chosen
    RESTORE
    mov al, byte ptr [rip + game_race_flag] # the replaced instruction
    ret
