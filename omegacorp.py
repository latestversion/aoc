
""" VirtualFury (TM), the powerful next generation Intcode processor """
from collections import defaultdict

class VirtualFury:
    STATUS_OK = 0
    STATUS_WAITING_FOR_INPUT = 1
    STATUS_PROGRAM_ENDED = 99
    STATUS_EXCEPTION = 3
    STATUS_BP = 4

    def __init__(self, program, inputed=[]):
        self.program = defaultdict(int)
        for i, p in enumerate(program):
            self.program[i] = p
        self.pc = 0
        self.output = 0
        self.num_flanks = 0
        self.last_opcode = 0
        self.status = VirtualFury.STATUS_OK
        self.num_flanks = 0
        self.input = inputed
        self.breakpoints = []
        self.snapshot = program.copy()
        self.relative_base = 0
        self.out_buffer = []

    def save_snapshot(self):
        self.snapshot = self.program.copy()

    def snapshot_diff(self):
        assert len(self.snapshot) == len(self.program)
        diffs = []
        for pc in range(0, len(self.snapshot)):
            old = self.snapshot[pc]
            new = self.program[pc]
            if old != new:
                diffs.append((pc, old, new))
        return diffs

    def p_snapshot_diff(self):
        diffs = self.snapshot_diff()
        for diff in diffs:
            print("{}: {} -> {}".format(diff[0], diff[1], diff[2]))

    def dump_ints(self, addr, rows, cols=4):
        assert rows > 0
        assert cols > 0

        for row in range(0, rows):
            s = "addr{} ".format(addr + row * cols)
            for col in range(0, cols):
                pointer = addr + row*cols + col
                if pointer not in self.program:
                    s += " OOM "
                else:
                    ins = self.program[pointer]
                    s += " {} ".format(ins)
            print(s)

    def dump(self, addr, rows, cols=4):
        self.dump_ints(addr, rows, cols)

    def bp(self, addr):
        if addr not in self.breakpoints:
            self.breakpoints.append(addr)

    def bp_clear(self, addr):
        self.breakpoints.remove(addr)

    def run(self, steps=None):
        # Check statuses set by opcodes first
        while (steps is None or steps > 0) and \
                self.status is not VirtualFury.STATUS_PROGRAM_ENDED and \
                self.status is not VirtualFury.STATUS_WAITING_FOR_INPUT:
            if self.pc in self.breakpoints:
                if self.status != VirtualFury.STATUS_BP:
                    self.status = VirtualFury.STATUS_BP
                    return
                else:
                    self.status = VirtualFury.STATUS_OK
            self.highflank()
            # DON'T set any statuses here, as it might overwrite what the opcodes set
            # TODO: Move breakpoint and exception indication to dedicated signals
            if steps is not None:
                steps -= 1

    def highflank(self):
        ins = self.program[self.pc]
        decoded = self.decode_instruction(ins)
        dpc = self.execute(decoded, self.program)

        self.pc += dpc

        self.num_flanks += 1

    def step(self):
        self.highflank()

    def decode_instruction(self, i):
        opcode = i % 100
        i -= opcode
        im1 = (i % 1000) // 100
        i -= im1
        im2 = (i % 10000) // 1000
        i -= im2
        im3 = (i % 100000) // 10000
        return opcode, im1, im2, im3

    def load(self, addr, mode):
        if addr < 0:
            self.status = VirtualFury.STATUS_EXCEPTION
            raise AddressOutOfBoundsException("Illegal load for pc = {}, addr = {}".format(self.pc, 4))
        val = self.program[addr]
        if mode == 0:
            if val < 0:
                self.status = VirtualFury.STATUS_EXCEPTION
                raise AddressOutOfBoundsException("Illegal load for pc = {}, addr = {}".format(self.pc, 4))
            val = self.program[val]
        elif mode == 2:
            val = self.program[val + self.relative_base]
        return val

    def store(self, addr, val):
        if addr < 0:
            self.status = VirtualFury.STATUS_EXCEPTION
            raise AddressOutOfBoundsException("Illegal store for pc = {}, addr = {}".format(self.pc, addr))
        self.program[addr] = val

    def provide_input_and_run(self, inputed):
        self.input.append(inputed)
        self.status = 0
        self.run()

    def execute(self, decoded, program):
        opcode = decoded[0]

        self.last_opcode = opcode

        if opcode == 1:
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            addr = program[self.pc + 3]
            if decoded[3] == 2:
                addr += self.relative_base
            self.store(addr, val1 + val2)
            # print("program[{}] = {} + {}".format(addr, val1, val2))
            return 4
        elif opcode == 2:
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            addr = program[self.pc + 3]
            if decoded[3] == 2:
                addr += self.relative_base
            self.store(addr, val1 * val2)
            # print("program[{}] = {} * {}".format(addr, val1, val2))
            return 4
        elif opcode == 3:
            if len(self.input) == 0:
                self.status = VirtualFury.STATUS_WAITING_FOR_INPUT
                return 0
            addr = program[self.pc + 1]
            if decoded[1] == 2:
                addr += self.relative_base
            self.store(addr, self.input.pop(0))
            # print("program[{}] = 5".format(addr))
            return 2
        elif opcode == 4:
            val = self.load(self.pc + 1, decoded[1])
            self.output = val
            self.out_buffer.append(val)
            return 2
        elif opcode == 5:  # jump-if-true
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            if val1 != 0:
                self.pc = val2
                return 0
            return 3
        elif opcode == 6:  # jump-if-false
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            if val1 == 0:
                self.pc = val2
                return 0
            return 3

        elif opcode == 7:  # less than
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            addr = program[self.pc + 3]
            if decoded[3] == 2:
                addr += self.relative_base
            if val1 < val2:
                self.store(addr, 1)
            else:
                self.store(addr, 0)
            return 4

        elif opcode == 8:  # equal
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            addr = program[self.pc + 3]
            if decoded[3] == 2:
                addr += self.relative_base
            if val1 == val2:
                self.store(addr, 1)
            else:
                self.store(addr, 0)
            return 4

        elif opcode == 9:
            val1 = self.load(self.pc + 1, decoded[1])
            self.relative_base += val1
            return 2

        elif opcode == 99:
            self.status = VirtualFury.STATUS_PROGRAM_ENDED
            return 0

        else:
            self.status = VirtualFury.STATUS_EXCEPTION
            msg = "Unknown opcode {} for pc = {}, *pc = {}".format(opcode, self.pc, self.program[self.pc])
            raise UnknownOpCodeException(msg)


class AddressOutOfBoundsException(Exception):
    pass


class UnknownOpCodeException(Exception):
    pass


print("Running VirtualFury Verification Suite 1.0")

__line = "3,225,1,225,6,6,1100,1,238,225,104,0,1102,72,20,224,1001,224,-1440,224,4,224,102,8,223,223,1001,224,5,224,1,224,223,223,1002,147,33,224,101,-3036,224,224,4,224,102,8,223,223,1001,224,5,224,1,224,223,223,1102,32,90,225,101,65,87,224,101,-85,224,224,4,224,1002,223,8,223,101,4,224,224,1,223,224,223,1102,33,92,225,1102,20,52,225,1101,76,89,225,1,117,122,224,101,-78,224,224,4,224,102,8,223,223,101,1,224,224,1,223,224,223,1102,54,22,225,1102,5,24,225,102,50,84,224,101,-4600,224,224,4,224,1002,223,8,223,101,3,224,224,1,223,224,223,1102,92,64,225,1101,42,83,224,101,-125,224,224,4,224,102,8,223,223,101,5,224,224,1,224,223,223,2,58,195,224,1001,224,-6840,224,4,224,102,8,223,223,101,1,224,224,1,223,224,223,1101,76,48,225,1001,92,65,224,1001,224,-154,224,4,224,1002,223,8,223,101,5,224,224,1,223,224,223,4,223,99,0,0,0,677,0,0,0,0,0,0,0,0,0,0,0,1105,0,99999,1105,227,247,1105,1,99999,1005,227,99999,1005,0,256,1105,1,99999,1106,227,99999,1106,0,265,1105,1,99999,1006,0,99999,1006,227,274,1105,1,99999,1105,1,280,1105,1,99999,1,225,225,225,1101,294,0,0,105,1,0,1105,1,99999,1106,0,300,1105,1,99999,1,225,225,225,1101,314,0,0,106,0,0,1105,1,99999,1107,677,226,224,1002,223,2,223,1005,224,329,101,1,223,223,7,677,226,224,102,2,223,223,1005,224,344,1001,223,1,223,1107,226,226,224,1002,223,2,223,1006,224,359,1001,223,1,223,8,226,226,224,1002,223,2,223,1006,224,374,101,1,223,223,108,226,226,224,102,2,223,223,1005,224,389,1001,223,1,223,1008,226,226,224,1002,223,2,223,1005,224,404,101,1,223,223,1107,226,677,224,1002,223,2,223,1006,224,419,101,1,223,223,1008,226,677,224,1002,223,2,223,1006,224,434,101,1,223,223,108,677,677,224,1002,223,2,223,1006,224,449,101,1,223,223,1108,677,226,224,102,2,223,223,1006,224,464,1001,223,1,223,107,677,677,224,102,2,223,223,1005,224,479,101,1,223,223,7,226,677,224,1002,223,2,223,1006,224,494,1001,223,1,223,7,677,677,224,102,2,223,223,1006,224,509,101,1,223,223,107,226,677,224,1002,223,2,223,1006,224,524,1001,223,1,223,1007,226,226,224,102,2,223,223,1006,224,539,1001,223,1,223,108,677,226,224,102,2,223,223,1005,224,554,101,1,223,223,1007,677,677,224,102,2,223,223,1006,224,569,101,1,223,223,8,677,226,224,102,2,223,223,1006,224,584,1001,223,1,223,1008,677,677,224,1002,223,2,223,1006,224,599,1001,223,1,223,1007,677,226,224,1002,223,2,223,1005,224,614,101,1,223,223,1108,226,677,224,1002,223,2,223,1005,224,629,101,1,223,223,1108,677,677,224,1002,223,2,223,1005,224,644,1001,223,1,223,8,226,677,224,1002,223,2,223,1006,224,659,101,1,223,223,107,226,226,224,102,2,223,223,1005,224,674,101,1,223,223,4,223,99,226"
__program = list(map(int, __line.split(",")))

__vm = VirtualFury(__program.copy(), [1])
__vm.run()
assert __vm.output == 11933517

__vm = VirtualFury(__program.copy(), [5])
__vm.run()
assert __vm.output == 10428568

__line = "3,21,1008,21,8,20,1005,20,22,107,8,21,20,1006,20,31,1106,0,36,98,0,0,1002,21,125,20,4,20,1105,1,46,104,999,1105,1,46,1101,1000,1,20,4,20,1105,1,46,98,99"
__program = list(map(int, __line.split(",")))

__vm = VirtualFury(__program.copy(), [7])
__vm.run()
assert __vm.output == 999

__vm = VirtualFury(__program.copy(), [8])
__vm.run()
assert __vm.output == 1000

__vm = VirtualFury(__program.copy(), [9])
__vm.run()
assert __vm.output == 1001

__line = "3,12,6,12,15,1,13,14,13,4,13,99,-1,0,1,9"
__program = list(map(int, __line.split(",")))

__vm = VirtualFury(__program.copy(), [0])
__vm.run()
assert __vm.output == 0

__vm = VirtualFury(__program.copy(), [9])
__vm.run()
assert __vm.output == 1

__line = "3,3,1105,-1,9,1101,0,0,12,4,12,99,1"
__program = list(map(int, __line.split(",")))

__vm = VirtualFury(__program.copy(), [0])
__vm.run()
assert __vm.output == 0

__vm = VirtualFury(__program.copy(), [9])
__vm.run()
assert __vm.output == 1

__line = "11,-1,1,20000"
__program = list(map(int, __line.split(",")))

try:
    __vm = VirtualFury(__program.copy(), [0])
    __vm.run()
except UnknownOpCodeException:
    assert __vm.status == VirtualFury.STATUS_EXCEPTION
else:
    assert 0

__program = [99]
__vm = VirtualFury(__program.copy(), [0])
__vm.bp(0)
__vm.run()
assert __vm.status == VirtualFury.STATUS_BP
__vm.run()
assert __vm.status == VirtualFury.STATUS_PROGRAM_ENDED

__program = [1101, 50, 50, 13, 1101, 50, 50, 13, 1101, 50, 50, 13, 99, 0]
__vm = VirtualFury(__program.copy(), [0])
__vm.bp(4)
__vm.bp(8)
__vm.run()
assert __vm.status == VirtualFury.STATUS_BP
assert __vm.pc == 4
__vm.bp_clear(8)
__vm.run()
assert __vm.status == VirtualFury.STATUS_PROGRAM_ENDED

__program = [1101, 1, 0, 13, 1101, 2, 0, 0, 1101, 3, 0, 4, 99, 0]
__vm = VirtualFury(__program.copy(), [0])
__vm.run()
__diffs = __vm.snapshot_diff()
assert __diffs[0] == (0, 1101, 2)
assert __diffs[1] == (4, 1101, 3)
assert __diffs[2] == (13, 0, 1)
assert len(__diffs) == 3
assert __vm.status == VirtualFury.STATUS_PROGRAM_ENDED

__program = [1101, 1, 0, 13, 1101, 2, 0, 0, 1101, 3, 0, 4, 99, 0]
__vm = VirtualFury(__program.copy(), [0])
__vm.bp(4)
__vm.run()
__diffs = __vm.snapshot_diff()
assert __diffs[0] == (13, 0, 1)
__vm.save_snapshot()
__vm.run()
__diffs = __vm.snapshot_diff()
assert __diffs[0] == (0, 1101, 2)
assert __diffs[1] == (4, 1101, 3)
assert len(__diffs) == 2
assert __vm.status == VirtualFury.STATUS_PROGRAM_ENDED

# Test run(2) runs 2 instructions
__program = [1101, 1, 0, 13, 1101, 2, 0, 0, 1101, 3, 0, 4, 99, 0]
__vm = VirtualFury(__program.copy())
__vm.run(2)
assert __vm.pc == 8
__vm.run()
assert __vm.status == VirtualFury.STATUS_PROGRAM_ENDED

# Test run(x) heeds breakpoints
__program = [1101, 1, 0, 13, 1101, 2, 0, 0, 1101, 3, 0, 4, 99, 0]
__vm = VirtualFury(__program.copy())
__vm.bp(4)
__vm.run(200)
assert __vm.status == VirtualFury.STATUS_BP
assert __vm.pc == 4
__vm.run()
assert __vm.status == VirtualFury.STATUS_PROGRAM_ENDED

# Day 9 examples

# Day 9 BigInt 1
__program = [1102,34915192,34915192,7,4,7,99,0]
__vm = VirtualFury(__program.copy())
__vm.run()
assert len(str(__vm.output)) == 16

# Day 9 BigInt 2
__program = [104,1125899906842624,99]
__vm = VirtualFury(__program.copy())
__vm.run()
assert __vm.output == 1125899906842624


# Day 9 BigMem
__program = [109,1,204,-1,1001,100,1,100,1008,100,16,101,1006,101,0,99]
__vm = VirtualFury(__program.copy())
__vm.run()
assert __vm.out_buffer == __program

# Day 9 Part 1
__program = [1102, 34463338, 34463338, 63, 1007, 63, 34463338, 63, 1005, 63, 53, 1102, 3, 1, 1000, 109, 988, 209, 12, 9, 1000, 209, 6, 209, 3, 203, 0, 1008, 1000, 1, 63, 1005, 63, 65, 1008, 1000, 2, 63, 1005, 63, 904, 1008, 1000, 0, 63, 1005, 63, 58, 4, 25, 104, 0, 99, 4, 0, 104, 0, 99, 4, 17, 104, 0, 99, 0, 0, 1102, 1, 38, 1003, 1102, 24, 1, 1008, 1102, 1, 29, 1009, 1102, 873, 1, 1026, 1102, 1, 32, 1015, 1102, 1, 1, 1021, 1101, 0, 852, 1023, 1102, 1, 21, 1006, 1101, 35, 0, 1018, 1102, 1, 22, 1019, 1102, 839, 1, 1028, 1102, 1, 834, 1029, 1101, 0, 36, 1012, 1101, 0, 31, 1011, 1102, 23, 1, 1000, 1101, 405, 0, 1024, 1101, 33, 0, 1013, 1101, 870, 0, 1027, 1101, 0, 26, 1005, 1101, 30, 0, 1004, 1102, 1, 39, 1007, 1101, 0, 28, 1017, 1101, 34, 0, 1001, 1102, 37, 1, 1014, 1101, 20, 0, 1002, 1102, 1, 0, 1020, 1101, 0, 859, 1022, 1102, 1, 27, 1016, 1101, 400, 0, 1025, 1102, 1, 25, 1010, 109, -6, 1207, 10, 29, 63, 1005, 63, 201, 1001, 64, 1, 64, 1105, 1, 203, 4, 187, 1002, 64, 2, 64, 109, 3, 2107, 25, 8, 63, 1005, 63, 221, 4, 209, 1106, 0, 225, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -4, 2101, 0, 9, 63, 1008, 63, 18, 63, 1005, 63, 245, 1106, 0, 251, 4, 231, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 3, 2108, 38, 7, 63, 1005, 63, 273, 4, 257, 1001, 64, 1, 64, 1106, 0, 273, 1002, 64, 2, 64, 109, 22, 21102, 40, 1, 0, 1008, 1018, 40, 63, 1005, 63, 299, 4, 279, 1001, 64, 1, 64, 1106, 0, 299, 1002, 64, 2, 64, 109, -16, 21108, 41, 41, 10, 1005, 1012, 321, 4, 305, 1001, 64, 1, 64, 1105, 1, 321, 1002, 64, 2, 64, 109, 6, 2102, 1, -2, 63, 1008, 63, 22, 63, 1005, 63, 341, 1105, 1, 347, 4, 327, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 21, 1206, -8, 359, 1106, 0, 365, 4, 353, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -7, 21101, 42, 0, -6, 1008, 1016, 44, 63, 1005, 63, 389, 1001, 64, 1, 64, 1105, 1, 391, 4, 371, 1002, 64, 2, 64, 109, 2, 2105, 1, 0, 4, 397, 1106, 0, 409, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -3, 1205, 0, 427, 4, 415, 1001, 64, 1, 64, 1105, 1, 427, 1002, 64, 2, 64, 109, -13, 2102, 1, -1, 63, 1008, 63, 39, 63, 1005, 63, 449, 4, 433, 1106, 0, 453, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -10, 1202, 4, 1, 63, 1008, 63, 20, 63, 1005, 63, 479, 4, 459, 1001, 64, 1, 64, 1106, 0, 479, 1002, 64, 2, 64, 109, 7, 2108, 37, -2, 63, 1005, 63, 495, 1105, 1, 501, 4, 485, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 4, 21101, 43, 0, 1, 1008, 1010, 43, 63, 1005, 63, 523, 4, 507, 1106, 0, 527, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -4, 1208, -5, 23, 63, 1005, 63, 549, 4, 533, 1001, 64, 1, 64, 1106, 0, 549, 1002, 64, 2, 64, 109, -4, 1208, 7, 27, 63, 1005, 63, 565, 1106, 0, 571, 4, 555, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 15, 1205, 4, 587, 1001, 64, 1, 64, 1106, 0, 589, 4, 577, 1002, 64, 2, 64, 109, -7, 1202, -7, 1, 63, 1008, 63, 18, 63, 1005, 63, 613, 1001, 64, 1, 64, 1106, 0, 615, 4, 595, 1002, 64, 2, 64, 109, 5, 21107, 44, 43, 1, 1005, 1015, 635, 1001, 64, 1, 64, 1105, 1, 637, 4, 621, 1002, 64, 2, 64, 109, -2, 21102, 45, 1, 6, 1008, 1018, 44, 63, 1005, 63, 661, 1001, 64, 1, 64, 1105, 1, 663, 4, 643, 1002, 64, 2, 64, 109, -18, 1207, 6, 24, 63, 1005, 63, 685, 4, 669, 1001, 64, 1, 64, 1105, 1, 685, 1002, 64, 2, 64, 109, 4, 2101, 0, 8, 63, 1008, 63, 21, 63, 1005, 63, 707, 4, 691, 1105, 1, 711, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 17, 1206, 5, 725, 4, 717, 1105, 1, 729, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 9, 21107, 46, 47, -9, 1005, 1015, 751, 4, 735, 1001, 64, 1, 64, 1106, 0, 751, 1002, 64, 2, 64, 109, -9, 1201, -6, 0, 63, 1008, 63, 26, 63, 1005, 63, 775, 1001, 64, 1, 64, 1106, 0, 777, 4, 757, 1002, 64, 2, 64, 109, -15, 1201, 0, 0, 63, 1008, 63, 23, 63, 1005, 63, 803, 4, 783, 1001, 64, 1, 64, 1105, 1, 803, 1002, 64, 2, 64, 109, -1, 2107, 30, 10, 63, 1005, 63, 819, 1106, 0, 825, 4, 809, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, 24, 2106, 0, 5, 4, 831, 1105, 1, 843, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -5, 2105, 1, 5, 1001, 64, 1, 64, 1105, 1, 861, 4, 849, 1002, 64, 2, 64, 109, 14, 2106, 0, -5, 1105, 1, 879, 4, 867, 1001, 64, 1, 64, 1002, 64, 2, 64, 109, -17, 21108, 47, 44, 4, 1005, 1019, 899, 1001, 64, 1, 64, 1105, 1, 901, 4, 885, 4, 64, 99, 21101, 0, 27, 1, 21102, 915, 1, 0, 1106, 0, 922, 21201, 1, 58969, 1, 204, 1, 99, 109, 3, 1207, -2, 3, 63, 1005, 63, 964, 21201, -2, -1, 1, 21101, 0, 942, 0, 1105, 1, 922, 22102, 1, 1, -1, 21201, -2, -3, 1, 21101, 957, 0, 0, 1106, 0, 922, 22201, 1, -1, -2, 1106, 0, 968, 21201, -2, 0, -2, 109, -3, 2105, 1, 0]
__vm = VirtualFury(__program.copy(), [1])
__vm.run()
assert __vm.output == 3235019597

# Day 9 Part 2
# __vm = VirtualFury(__program.copy(), [2])
# __vm.run()
# assert __vm.output == 80274

print("VirtualFury Verification Suite 1.0 Ended")