#!/usr/bin/env python3
"""Implementation of a brainfuck interpreter."""
from dataclasses import dataclass, field, InitVar
from collections import deque
from sys import exit as sysexit
import click

_CMDS = {}


def make_cmd(name):
    """Create a command with the given name."""

    def add_to_dict(func):
        """Add the given function to the map of commands."""
        _CMDS[name] = func

    return add_to_dict


@dataclass
class BFInterpreter:
    """Brainfuck interpreter with pretty printing."""

    # Constants
    chunk_size = 32

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
    program_counter: int = 0
    addr_offset: int = 0
    jumps: dict = field(default_factory=dict)

    def __post_init__(self, window_start, tape):
        """Initialize interpreter configuration parameters."""
        self.window_start = self.addr_ptr - self.margin
        self.tape = deque([0] * self.chunk_size)

    def evaluate(self, code):
        """Evaluate a fragment of brainfuck code."""
        self.program_counter = 0
        code = self.preprocess(code)
        steps = 0
        while self.program_counter < len(code):
            steps += 1
            try:
                _CMDS[code[self.program_counter]](self)
                self.program_counter += 1
                if self.showmem:
                    self.print_tape()
                if self.stepbystep and self.fromfile:
                    input("Enter to continue to next step...")
            except KeyError:
                pass
        print(f"\nCompleted in {steps} steps.")

    def preprocess(self, code):
        """Preprocess brainfuck source.

        Remove comments and save jump locations.
        """
        legalchars = ",.<>+-[]"
        code = "".join([i for i in code if i in legalchars])
        self.jumps.clear()
        opens = deque()
        for idx, char in enumerate(code):
            if char == "[":
                opens.append(idx)
            elif char == "]":
                self.jumps[opens.pop()] = idx
        return code

    def get_cell(self, idx):
        """Get the value of the idx-th cell."""
        tmp = idx + self.addr_offset
        return self.tape[tmp] if 0 <= tmp < len(self.tape) else 0

    def get_current_cell(self):
        """Get the value at the cell pointed to by the head."""
        return self.get_cell(self.addr_ptr)

    def set_current_cell(self, val):
        """Set the value of the cell pointed to by the head."""
        self.tape[self.addr_ptr + self.addr_offset] = val

    def modify_current_cell(self, func):
        """Call func on the cell pointed to by the head."""
        self.set_current_cell(func(self.get_current_cell()))

    def print_tape(self):
        """Pretty print the memory tape using configuration parameters."""
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
        """Print the borders of the memory tape."""
        print(f"{'+-----' * self.window_size}+")

    def shift_window(self, left=False):
        """Shift the view of the window by one cell to the left/right."""
        self.window_start += 1 if not left else -1

    def add_cells_left(self):
        """Extend tape memory by CHUNK_SIZE cells to the left."""
        self.tape.extendleft([0 for i in range(self.chunk_size)])
        self.addr_offset += self.chunk_size

    def add_cells_right(self):
        """Extend tape memory by CHUNK_SIZE cells to the right."""
        self.tape.extend([0 for i in range(self.chunk_size)])

    @make_cmd("<")
    def move_left(self):
        """Move the head left.

        Extends memory and shifts the print view as needed.
        """
        if self.verbose:
            print(
                "Moving the head left from cell"
                f"{self.addr_ptr} to {self.addr_ptr-1}."
            )
        self.addr_ptr -= 1
        if self.addr_ptr - self.window_start < self.margin:
            self.shift_window(left=True)
        if self.addr_ptr < 0:
            self.add_cells_left()

    @make_cmd(">")
    def move_right(self):
        """Move the head right.

        Extends memory and shifts the print view as needed.
        """
        if self.verbose:
            print(
                "Moving the head right from cell"
                f"{self.addr_ptr} to {self.addr_ptr+1}."
            )
        self.addr_ptr += 1
        if self.window_start + self.window_size - self.addr_ptr <= self.margin:
            self.shift_window()
        if self.addr_ptr >= len(self.tape):
            self.add_cells_right()

    @make_cmd(".")
    def write(self):
        """Print the value of the cell pointed to by the head."""
        func = chr if not self.printraw else lambda x: x
        if self.verbose:
            print("Writing cell to stdout.")
        print(func(self.get_current_cell()), end="" if self.fromfile else "\n")

    @make_cmd(",")
    def read(self):
        """Write a char read from stdin to the cell pointed to by head."""
        if self.verbose:
            print("Waiting for input...")
        self.set_current_cell(int(input()) % 2 ** 8)

    @make_cmd("+")
    def inc(self):
        """Increment the value of the cell pointed to by the head."""
        if self.verbose:
            print("Incrementing the current cell.")
        self.modify_current_cell(lambda x: x + 1)
        self.modify_current_cell(lambda x: x % 2 ** 8)

    @make_cmd("-")
    def dec(self):
        """Decrement the value of the cell pointed to by the head."""
        if self.verbose:
            print("Decrementing the current cell.")
        self.modify_current_cell(lambda x: x - 1)
        if self.get_current_cell() < 0:
            self.modify_current_cell(lambda x: x + 2 ** 8)

    @make_cmd("[")
    def jump_if_zero(self):
        """Jump to the matching ']' if the current cell is zero."""
        if not self.get_current_cell():
            if self.verbose:
                print(
                    "Jumping to instruction "
                    f"{self.jumps[self.program_counter]}"
                )
            self.program_counter = self.jumps[self.program_counter]
        elif self.verbose:
            print("Current cell is not 0. Not jumping.")

    @make_cmd("]")
    def jump_unless_zero(self):
        """Jump to the matching '[' if the current cell is not zero."""
        if self.get_current_cell():
            tmp = next(
                key for key, value in self.jumps.items()
                if value == self.program_counter
            )
            if self.verbose:
                print(f"Jumping to instruction {tmp}.")
            # Slow, need better DS?
            self.program_counter = tmp
        elif self.verbose:
            print("Current cell is 0. Not jumping.")


@click.command()
@click.argument("files", nargs=-1, required=False)
@click.option(
    "--step-by-step",
    "-s",
    is_flag=True,
    help="Execute each instruction one by one, "
    "waiting for user confirmation to continue to the next",
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
    help="Minimum number of cells away the head needs "
    "to be to shift the print window",
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
    """CLI for the interpreter."""
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
        except (FileNotFoundError, EOFError, KeyboardInterrupt) as error:
            print(error)
    else:
        try:
            while True:
                source = input("bf> ")
                bf_int.evaluate(source)
        except (EOFError, KeyboardInterrupt):
            print("Goodbye")
            sysexit(0)


# TODO option for separate memories for each source file inputted
# TODO Interpreter holds list of objects that carry out optional cmdline args
# TODO put driver into main function
# TODO handle jumps on the fly with stack, remove need for preprocessing
# TODO add option to dump stdout output after program execution
if __name__ == "__main__":
    main()
