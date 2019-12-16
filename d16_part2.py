
from aocd import get_data

line = get_data(day=16, year=2019)

offset = int(line[0:7])
input = list(map(int, [d for d in line]))

length = len(input)*10000

big_input = [input[x%len(input)] for x in range(offset, length)]

assert len(big_input) == length - offset

# Elements with index i after half the length is equal to sum([i:])
assert offset > length/2

for _ in range(100):

    for i, e in reversed(list(enumerate(big_input))):
        if i == len(big_input)-1:
            pass
        else:
            big_input[i] += big_input[i+1]
            big_input[i] = big_input[i]%10

    print(_)

print("".join(list(map(str, big_input[:8]))))

#The key to it all:
# 12345

#  1 0 0 0 0
#  0 1 0 0 0
# -1 1 1 0 0
#  0 0 1 1 0
#  1 0 1 1 1