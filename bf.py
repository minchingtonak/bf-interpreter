#!/usr/bin/python3.7

from dataclasses import dataclass, field
from typing import List
from collections import deque

_CMDS = {}


def make_cmd(name):
    def add_to_dict(func, *args, **kwargs):
        _CMDS[name] = func

    return add_to_dict


@dataclass
class BFInterpreter:
    stepbystep: bool
    window_size: int
    margin: int

    chunk_size: int = 32
    tape: deque = deque([0 for i in range(32)])
    addr_ptr: int = 0
    pc: int = 0
    source: str = str()
    jumps: dict = field(default_factory=dict)

    def evaluate(self, code):
        self.source = code
        self.preprocess(self.source)
        while self.pc < len(self.source):
            try:
                _CMDS[self.source[self.pc]](self)
            except KeyError:
                pass
            self.pc += 1

    def preprocess(self, code):
        self.jumps.clear()
        opens = deque()
        for idx, c in enumerate(code):
            if c == "[":
                opens.append(idx)
            elif c == "]":
                self.jumps[opens.pop()] = idx

    def print_tape(self):
        pass

    @make_cmd("<")
    def move_left(self):
        self.addr_ptr -= 1
        if self.addr_ptr < 0:
            self.tape.extendleft([0 for i in range(self.chunk_size)])
            self.addr_ptr = self.chunk_size - 1

    @make_cmd(">")
    def move_right(self):
        self.addr_ptr += 1
        if self.addr_ptr > len(self.tape):
            self.tape.extend([0 for i in range(self.chunk_size)])

    @make_cmd(".")
    def write(self):
        print(chr(self.tape[self.addr_ptr]), end="")

    @make_cmd(",")
    def read(self):
        self.tape[self.addr_ptr] = int(input()) % 2 ** 8

    @make_cmd("+")
    def inc(self):
        self.tape[self.addr_ptr] += 1
        self.tape[self.addr_ptr] %= 2 ** 8

    @make_cmd("-")
    def dec(self):
        self.tape[self.addr_ptr] -= 1
        if self.tape[self.addr_ptr] < 0:
            self.tape[self.addr_ptr] += 2 ** 8

    @make_cmd("[")
    def jump_if_zero(self):
        if not self.tape[self.addr_ptr]:
            self.pc = self.jumps[self.pc]

    @make_cmd("]")
    def jump_unless_zero(self):
        if self.tape[self.addr_ptr]:
            # Slow, need better DS?
            self.pc = next(
                key for key, value in self.jumps.items() if value == self.pc
            )


# TODO option for separate memories for each source file inputted
if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="A simple brainfuck interpreter.")

    parser.add_argument(
        "file", help="brainfuck source file(s) to execute", nargs="*"
    )
    parser.add_argument(
        "--step-by-step",
        "-s",
        action="store_false",
        help="Execute each instruction one by one, waiting for user confirmation to continue to the next",
    )
    parser.add_argument(
        "--print-range",
        "-pr",
        const=3,
        type=int,
        nargs="?",
        help="size of the window of memory cells that will be printed. default 10",
    )
    parser.add_argument(
        "--head-margin",
        "-hm",
        const=2,
        type=int,
        nargs="?",
        help="minimum number of cells away the head needs to be to shift the print window",
    )

    parsed_args = parser.parse_args()

    bf_int = BFInterpreter(
        stepbystep=parsed_args.step_by_step,
        window_size=parsed_args.print_range,
        margin=parsed_args.head_margin,
    )

    if parsed_args.file:
        with open(parsed_args.file, "r") as file:
            bf_int.evaluate(file.read())
    else:
        try:
            while True:
                source = input("bf> ")
                bf_int.evaluate(source)
        except (EOFError, KeyboardInterrupt):
            print("Goodbye")
            exit(0)
