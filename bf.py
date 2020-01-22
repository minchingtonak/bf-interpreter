#!/usr/bin/python3.7

from dataclasses import dataclass, field, InitVar
from typing import List
from collections import deque
import click

_CMDS = {}


def make_cmd(name):
    def add_to_dict(func, *args, **kwargs):
        _CMDS[name] = func

    return add_to_dict


@dataclass
class BFInterpreter:
    # Constants
    CHUNK_SIZE = 32

    # Configuration
    stepbystep: bool
    showmem: bool
    window_size: int
    margin: int
    verbose: bool
    printraw: bool
    fromfile: bool

    # Interpreter parameters
    window_start: InitVar[int] = None
    tape: InitVar[deque] = None
    addr_ptr: int = 0
    pc: int = 0
    addr_offset: int = 0
    jumps: dict = field(default_factory=dict)

    def __post_init__(self, window_start, tape):
        self.window_start = self.addr_ptr - self.margin
        self.tape = deque([0 for i in range(BFInterpreter.CHUNK_SIZE)])

    def evaluate(self, code):
        self.pc = 0
        code = self.preprocess(code)
        steps = 0
        while self.pc < len(code):
            steps += 1
            try:
                _CMDS[code[self.pc]](self)
                self.pc += 1
                if self.showmem:
                    self.print_tape()
                if self.stepbystep and self.fromfile:
                    input("Enter to continue to next step...")
            except KeyError:
                pass
        print(f"\nCompleted in {steps} steps.")

    def preprocess(self, code):
        legalchars = ',.<>+-[]'
        code = ''.join([i for i in code if i in legalchars])
        self.jumps.clear()
        opens = deque()
        for idx, c in enumerate(code):
            if c == "[":
                opens.append(idx)
            elif c == "]":
                self.jumps[opens.pop()] = idx
        return code

    def get_cell(self, idx):
        tmp = idx + self.addr_offset
        return self.tape[tmp] if tmp >= 0 and tmp < len(self.tape) else 0

    def get_current_cell(self):
        return self.get_cell(self.addr_ptr)

    def set_current_cell(self, val):
        self.tape[self.addr_ptr + self.addr_offset] = val

    def modify_current_cell(self, func):
        self.set_current_cell(func(self.get_current_cell()))

    def print_tape(self):
        print("\n  {:^3}".format(self.window_start), end="")
        for i in range(
            self.window_start + 1, self.window_start + self.window_size
        ):
            print("   {:^3}".format(i), end="")
        print()
        self.print_border()
        for i in range(
            self.window_start, self.window_start + self.window_size
        ):
            print(
                "| {0:^3} ".format(self.get_cell(i)), end="",
            )
        print("|")
        self.print_border()
        print(f"{'      ' * (self.addr_ptr - self.window_start)}   ^")

    def print_border(self):
        print(f"{'+-----' * self.window_size}+")

    def shift_window(self, left=False):
        self.window_start += 1 if not left else -1

    def add_cells_left(self):
        self.tape.extendleft([0 for i in range(BFInterpreter.CHUNK_SIZE)])
        self.addr_offset += BFInterpreter.CHUNK_SIZE

    def add_cells_right(self):
        self.tape.extend([0 for i in range(BFInterpreter.CHUNK_SIZE)])

    @make_cmd("<")
    def move_left(self):
        if self.verbose:
            print(
                f"Moving the head left from cell {self.addr_ptr} to {self.addr_ptr-1}."
            )
        self.addr_ptr -= 1
        if self.addr_ptr - self.window_start < self.margin:
            self.shift_window(left=True)
        if self.addr_ptr < 0:
            self.add_cells_left()

    @make_cmd(">")
    def move_right(self):
        if self.verbose:
            print(
                f"Moving the head right from cell {self.addr_ptr} to {self.addr_ptr+1}."
            )
        self.addr_ptr += 1
        if self.window_start + self.window_size - self.addr_ptr <= self.margin:
            self.shift_window()
        if self.addr_ptr >= len(self.tape):
            self.add_cells_right()

    @make_cmd(".")
    def write(self):
        f = chr if not self.printraw else lambda x: x
        if self.verbose:
            print("Writing cell to stdout.")
        print(f(self.get_current_cell()), end="" if self.fromfile else "\n")

    @make_cmd(",")
    def read(self):
        if self.verbose:
            print("Waiting for input...")
        self.set_current_cell(int(input()) % 2 ** 8)

    @make_cmd("+")
    def inc(self):
        if self.verbose:
            print("Incrementing the current cell.")
        self.modify_current_cell(lambda x: x + 1)
        self.modify_current_cell(lambda x: x % 2 ** 8)

    @make_cmd("-")
    def dec(self):
        if self.verbose:
            print("Decrementing the current cell.")
        self.modify_current_cell(lambda x: x - 1)
        if self.get_current_cell() < 0:
            self.modify_current_cell(lambda x: x + 2 ** 8)

    @make_cmd("[")
    def jump_if_zero(self):
        if not self.get_current_cell():
            if self.verbose:
                print(f"Jumping to instruction {self.jumps[self.pc]}")
            self.pc = self.jumps[self.pc]
        elif self.verbose:
            print("Current cell is not 0. Not jumping.")

    @make_cmd("]")
    def jump_unless_zero(self):
        if self.get_current_cell():
            tmp = next(
                key for key, value in self.jumps.items() if value == self.pc
            )
            if self.verbose:
                print(f"Jumping to instruction {tmp}.")
            # Slow, need better DS?
            self.pc = tmp
        elif self.verbose:
            print("Current cell is 0. Not jumping.")


@click.command()
@click.argument("files", nargs=-1, required=False)
@click.option(
    "--step-by-step",
    "-s",
    is_flag=True,
    help="Execute each instruction one by one, waiting for user confirmation to continue to the next",
)
@click.option(
    "--print-window",
    "-pw",
    type=int,
    default=10,
    help="Size of the window of memory cells that will be printed",
)
@click.option(
    "--head-margin",
    "-hm",
    type=int,
    default=2,
    help="Minimum number of cells away the head needs to be to shift the print window",
)
@click.option(
    "--show-memory",
    "-sm",
    is_flag=True,
    help="Print contents of memory near the head at each execution step",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Print description of each instruction executed",
)
@click.option(
    "--print-raw",
    "-r",
    is_flag=True,
    help="Print character representation of cells",
)
def main(
    files,
    step_by_step,
    print_window,
    head_margin,
    show_memory,
    verbose,
    print_raw,
):
    """A simple brainfuck interpreter."""
    bf_int = BFInterpreter(
        stepbystep=step_by_step,
        showmem=show_memory,
        window_size=print_window,
        margin=head_margin,
        verbose=verbose,
        printraw=print_raw,
        fromfile=len(files),
    )

    if files:
        try:
            for filename in files:
                with open(filename, "r") as file:
                    bf_int.evaluate(file.read())
        except (FileNotFoundError, EOFError, KeyboardInterrupt) as e:
            print(e)
    else:
        try:
            while True:
                source = input("bf> ")
                bf_int.evaluate(source)
        except (EOFError, KeyboardInterrupt):
            print("Goodbye")
            exit(0)


# TODO option for separate memories for each source file inputted
# TODO Interpreter holds list of objects that carry out optional cmdline args
# TODO put driver into main function
# TODO handle jumps on the fly with stack, remove need for preprocessing
# TODO add option to dump stdout output after program execution
if __name__ == "__main__":
    main()
