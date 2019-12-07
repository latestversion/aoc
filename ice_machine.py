
class IceMachine:
    STATUS_WAITING_FOR_INPUT = 1
    STATUS_PROGRAM_ENDED = 2
    STATUS_EXCEPTION = 3

    def __init__(self, program, inputed):
        self.program = program
        self.pc = 0
        self.output = 0
        self.num_flanks = 0
        self.last_opcode = 0
        self.status = 0
        self.num_flanks = 0
        self.input = inputed
        self.breakpoints = []

    def dump_ints(self, addr, rows, cols=4):
        assert rows > 0
        assert cols > 0

        for row in range(0, rows):
            s = "{} ".format(addr + row * cols)
            for col in range(0, cols):
                pointer = addr + row*cols + col
                if pointer >= len(self.program):
                    s += " OOM "
                else:
                    ins = self.program[pointer]
                    s += " {} ".format(ins)
            print(s)

    def run(self):
        while self.status is not IceMachine.STATUS_PROGRAM_ENDED and self.status is not IceMachine.STATUS_WAITING_FOR_INPUT and self.pc not in self.breakpoints:
            self.highflank()

    def highflank(self):
        ins = self.program[self.pc]
        decoded = self.decode_instruction(ins)
        dpc = self.execute(decoded, self.program)

        self.pc += dpc
        self.num_flanks += 1

        # naming convention a tad asymmetric
    def readAndClearOutput(self):
        tmp = self.output
        self.output = 0
        return tmp

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
        if addr < 0 or addr >= len(self.program):
            self.status = IceMachine.STATUS_EXCEPTION
            raise AddressOutOfBoundsException("Illegal load for pc = {}".format(self.pc))
        val = self.program[addr]
        if mode == 0:
            if val < 0 or val >= len(self.program):
                self.status = IceMachine.STATUS_EXCEPTION
                raise AddressOutOfBoundsException("Illegal load for pc = {}".format(self.pc))
            val = self.program[val]
        return val

    def store(self, addr, val):
        if addr < 0 or addr >= len(self.program):
            self.status = IceMachine.STATUS_EXCEPTION
            raise AddressOutOfBoundsException("Illegal store for pc = {}".format(self.pc))
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
            self.store(addr, val1 + val2)
            # print("program[{}] = {} + {}".format(addr, val1, val2))
            return 4
        elif opcode == 2:
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            addr = program[self.pc + 3]
            self.store(addr, val1 * val2)
            # print("program[{}] = {} * {}".format(addr, val1, val2))
            return 4
        elif opcode == 3:
            if len(self.input) == 0:
                self.status = IceMachine.STATUS_WAITING_FOR_INPUT
                return 0
            addr = program[self.pc + 1]
            self.store(addr, self.input.pop(0))
            #print("program[{}] = 5".format(addr))
            return 2
        elif opcode == 4:
            val = self.load(self.pc + 1, decoded[1])
            self.output = val
            if self.output == 0:
                self.last_ok_output_pc = self.pc
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
            if val1 < val2:
                self.store(addr, 1)
            else:
                self.store(addr, 0)
            return 4

        elif opcode == 8:  # equal
            val1 = self.load(self.pc + 1, decoded[1])
            val2 = self.load(self.pc + 2, decoded[2])
            addr = program[self.pc + 3]
            if val1 == val2:
                self.store(addr, 1)
            else:
                self.store(addr, 0)
            return 4

        elif opcode == 99:
            self.status = IceMachine.STATUS_PROGRAM_ENDED
            return 0

        else:
            self.status = IceMachine.STATUS_EXCEPTION
            raise UnknownOpCodeException("Unknown opcode {} for pc = {}".format(opcode, self.pc))

class AddressOutOfBoundsException(Exception):
    pass

class UnknownOpCodeException(Exception):
    pass

print("Running IceMachine Verification Suite 0.1")

__line = "3,225,1,225,6,6,1100,1,238,225,104,0,1102,72,20,224,1001,224,-1440,224,4,224,102,8,223,223,1001,224,5,224,1,224,223,223,1002,147,33,224,101,-3036,224,224,4,224,102,8,223,223,1001,224,5,224,1,224,223,223,1102,32,90,225,101,65,87,224,101,-85,224,224,4,224,1002,223,8,223,101,4,224,224,1,223,224,223,1102,33,92,225,1102,20,52,225,1101,76,89,225,1,117,122,224,101,-78,224,224,4,224,102,8,223,223,101,1,224,224,1,223,224,223,1102,54,22,225,1102,5,24,225,102,50,84,224,101,-4600,224,224,4,224,1002,223,8,223,101,3,224,224,1,223,224,223,1102,92,64,225,1101,42,83,224,101,-125,224,224,4,224,102,8,223,223,101,5,224,224,1,224,223,223,2,58,195,224,1001,224,-6840,224,4,224,102,8,223,223,101,1,224,224,1,223,224,223,1101,76,48,225,1001,92,65,224,1001,224,-154,224,4,224,1002,223,8,223,101,5,224,224,1,223,224,223,4,223,99,0,0,0,677,0,0,0,0,0,0,0,0,0,0,0,1105,0,99999,1105,227,247,1105,1,99999,1005,227,99999,1005,0,256,1105,1,99999,1106,227,99999,1106,0,265,1105,1,99999,1006,0,99999,1006,227,274,1105,1,99999,1105,1,280,1105,1,99999,1,225,225,225,1101,294,0,0,105,1,0,1105,1,99999,1106,0,300,1105,1,99999,1,225,225,225,1101,314,0,0,106,0,0,1105,1,99999,1107,677,226,224,1002,223,2,223,1005,224,329,101,1,223,223,7,677,226,224,102,2,223,223,1005,224,344,1001,223,1,223,1107,226,226,224,1002,223,2,223,1006,224,359,1001,223,1,223,8,226,226,224,1002,223,2,223,1006,224,374,101,1,223,223,108,226,226,224,102,2,223,223,1005,224,389,1001,223,1,223,1008,226,226,224,1002,223,2,223,1005,224,404,101,1,223,223,1107,226,677,224,1002,223,2,223,1006,224,419,101,1,223,223,1008,226,677,224,1002,223,2,223,1006,224,434,101,1,223,223,108,677,677,224,1002,223,2,223,1006,224,449,101,1,223,223,1108,677,226,224,102,2,223,223,1006,224,464,1001,223,1,223,107,677,677,224,102,2,223,223,1005,224,479,101,1,223,223,7,226,677,224,1002,223,2,223,1006,224,494,1001,223,1,223,7,677,677,224,102,2,223,223,1006,224,509,101,1,223,223,107,226,677,224,1002,223,2,223,1006,224,524,1001,223,1,223,1007,226,226,224,102,2,223,223,1006,224,539,1001,223,1,223,108,677,226,224,102,2,223,223,1005,224,554,101,1,223,223,1007,677,677,224,102,2,223,223,1006,224,569,101,1,223,223,8,677,226,224,102,2,223,223,1006,224,584,1001,223,1,223,1008,677,677,224,1002,223,2,223,1006,224,599,1001,223,1,223,1007,677,226,224,1002,223,2,223,1005,224,614,101,1,223,223,1108,226,677,224,1002,223,2,223,1005,224,629,101,1,223,223,1108,677,677,224,1002,223,2,223,1005,224,644,1001,223,1,223,8,226,677,224,1002,223,2,223,1006,224,659,101,1,223,223,107,226,226,224,102,2,223,223,1005,224,674,101,1,223,223,4,223,99,226"
__program = list(map(int, __line.split(",")))

__vm = IceMachine(__program.copy(), [1])
__vm.run()
assert __vm.output == 11933517

__vm = IceMachine(__program.copy(), [5])
__vm.run()
assert __vm.output == 10428568

__line = "3,21,1008,21,8,20,1005,20,22,107,8,21,20,1006,20,31,1106,0,36,98,0,0,1002,21,125,20,4,20,1105,1,46,104,999,1105,1,46,1101,1000,1,20,4,20,1105,1,46,98,99"
__program = list(map(int, __line.split(",")))

__vm = IceMachine(__program.copy(), [7])
__vm.run()
assert __vm.output == 999

__vm = IceMachine(__program.copy(), [8])
__vm.run()
assert __vm.output == 1000

__vm = IceMachine(__program.copy(), [9])
__vm.run()
assert __vm.output == 1001

__line = "3,12,6,12,15,1,13,14,13,4,13,99,-1,0,1,9"
__program = list(map(int, __line.split(",")))

__vm = IceMachine(__program.copy(), [0])
__vm.run()
assert __vm.output == 0

__vm = IceMachine(__program.copy(), [9])
__vm.run()
assert __vm.output == 1

__line = "3,3,1105,-1,9,1101,0,0,12,4,12,99,1"
__program = list(map(int, __line.split(",")))

__vm = IceMachine(__program.copy(), [0])
__vm.run()
assert __vm.output == 0

__vm = IceMachine(__program.copy(), [9])
__vm.run()
assert __vm.output == 1

__line = "8,0,20000"
__program = list(map(int, __line.split(",")))

try:
    __vm = IceMachine(__program.copy(), [0])
    __vm.run()
except Exception:
    pass
else:
    assert 0

__line = "1,0,1,20000"
__program = list(map(int, __line.split(",")))

try:
    __vm = IceMachine(__program.copy(), [0])
    __vm.run()
except AddressOutOfBoundsException:
    assert __vm.status == IceMachine.STATUS_EXCEPTION
else:
    assert 0

__line = "101,-1,1,20000"
__program = list(map(int, __line.split(",")))

try:
    __vm = IceMachine(__program.copy(), [0])
    __vm.run()
except AddressOutOfBoundsException:
    assert __vm.status == IceMachine.STATUS_EXCEPTION
else:
    assert 0

__line = "11,-1,1,20000"
__program = list(map(int, __line.split(",")))

try:
    __vm = IceMachine(__program.copy(), [0])
    __vm.run()
except UnknownOpCodeException:
    assert __vm.status == IceMachine.STATUS_EXCEPTION
else:
    assert 0