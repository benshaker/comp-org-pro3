#!/usr/bin/env python3
# simulate.py

import sys, argparse

# loop through each possible combination
def main(args):

    # pull in our (default) filename
    fn = args.file_name

    try:
        f = open(fn, "r")
    except FileNotFoundError:
        print("There was no file named \"" + fn + "\" at the path provided. Try asking for --help.")
        return

    lines = list(f)
    instructions = list()
    for line in lines:
        line = line.replace('\n', '')
        read_or_write, address = line.split()
        instruction = (read_or_write, address)
        instructions.append(instruction)
    # print(instructions)

    # define all possible settings for the cache
    cache_sizes = (1024, 4096, 65536, 131072)
    block_sizes = (8, 16, 32, 128)
    cache_placement_types = ("DM", "2W", "4W", "FA")
    write_back_policies = ("WB", "WT")

    for total_sz in cache_sizes:
      for blk_sz in block_sizes:
        for plcmt_type in cache_placement_types:
          for wb_policy in write_back_policies:
            # run the cache evaluator for each possible settings combo
            cache_eval(total_sz, blk_sz, plcmt_type, wb_policy, instructions)


def cache_eval(total_sz, blk_sz, plcmt_type, wb_policy, instructions):
    # create the empty cache to spec
    # read in the r/w instructions
    # record the interactions between those instrutions and the cache
    # print these results for the user
    # print(total_sz, blk_sz, plcmt_type, wb_policy)
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='\"simulate.py\" determines the cache efficiency, under a variety of different settings, for some provided set of test instructions.\n\n'+
        'Test instructions should be in the following format:\n'+
        'read 0x02000006\n'+
        'read 0x04000004\n'+
        'write 0x02000007\n'+
        '... &c', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--file_name',
                        '-fn',
                        help="the filename to be read for R/W instructions. The default value (when no other value is provided) is \'./test1.trace\'",
                        type=str,
                        default="test1.trace")

    main(parser.parse_args(sys.argv[1:]))