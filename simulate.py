#!/usr/bin/env python3
# simulate.py
# Ben Shaker | May 4th, 2019

import sys
import argparse
from math import log2

# global variables for ease of use
hit_counter = 0
miss_counter = 0
cache_to_main_bytes = 0
main_to_cache_bytes = 0


def main(args):

    # pull in our (default) filenames
    input_file = args.input_file
    output_file = args.output_file

    # grab all of the instructions from the input file
    instructions = get_instructions(input_file)

    # create the output file if it does not exist
    # clear the output file if it already exists
    open(output_file, "w+").close()
    # prepare the output file for appending
    f = open(output_file, "a")

    # define all possible settings for our cache
    cache_sizes = (1024, 4096, 65536, 131072)
    block_sizes = (8, 16, 32, 128)
    cache_placement_types = (("DM", 1), ("2W", 2), ("4W", 4), ("FA", 0))
    write_back_policies = (("WB", 0), ("WT", 1))

    # let's loop through each possible settings combo
    for total_sz in cache_sizes:
        for blk_sz in block_sizes:
            for plcmt_type in cache_placement_types:

                codename, n_way = plcmt_type
                if codename is not "FA":
                    # n-way associativity is provided
                    pass
                else:
                    # n-way associativity needs to be calculated
                    n_way = total_sz / blk_sz

                for wb_policy in write_back_policies:
                    # create a cache given these particular settings
                    bookshelf = create_bookshelf(total_sz, blk_sz, n_way)

                    # evaluate this cache with the provided instructions
                    results = testing_bookshelf(
                        bookshelf, wb_policy, instructions)
                    hit_count, m2c_byte_count, c2m_byte_count = results

                    # format our results for a clean output
                    policy, _ = wb_policy
                    block_count = bookshelf['num_blocks_per_set']
                    hit_percent = hit_count / len(instructions)
                    hit_percent = round(hit_percent, 2)

                    # print this output to our provided file
                    print(str(total_sz) + "\t"
                          + str(blk_sz) + "\t"
                          + str(codename) + "\t"
                          + str(policy) + "\t"
                          + str(hit_percent) + "\t"
                          + str(m2c_byte_count) + "\t"
                          + str(c2m_byte_count) + "\t"
                          + str(block_count),
                          file=f)

                    # empty the cache now that we're done using it
                    bookshelf.clear()

    # close the file that we have been writing to
    f.close()


def testing_bookshelf(bookshelf, wb_policy, instructions):

    # announce our desire to edit the global variables
    global hit_counter
    global miss_counter
    global cache_to_main_bytes
    global main_to_cache_bytes

    # reset all of the variables to zero
    hit_counter = 0
    miss_counter = 0
    cache_to_main_bytes = 0
    main_to_cache_bytes = 0

    # prepare our working variables
    _, write_thru = wb_policy

    shelf = bookshelf['data']
    num_sets = bookshelf['num_sets']
    num_tag_bits = bookshelf['num_tag_bits']
    num_index_bits = bookshelf['num_index_bits']
    num_offset_bits = bookshelf['num_offset_bits']

    offset_mask = 2 ** num_offset_bits - 1

    index_mask = 2 ** num_index_bits - 1
    index_mask = index_mask << num_offset_bits

    tag_mask = 2 ** num_tag_bits - 1
    tag_mask = tag_mask << (num_offset_bits + num_index_bits)

    # handle each instruction in the order they were received
    for instruction in instructions:
        # deconstruct the instruction
        read_or_write, address = instruction
        full_address = int(address, 16)

        # prepare our working variables
        this_offset = full_address & offset_mask
        this_index = full_address & index_mask
        this_tag = full_address & tag_mask

        found_or_replaced = False
        oldest_blk = (0, 0)
        empty_blocks = []

        # only interested in this set index
        set_of_blks = shelf[this_index]

        # for each block in this set
        for blk_num, block in enumerate(set_of_blks):
            if not block:
                # if the block is empty
                empty_blocks.append(blk_num)
                continue  # then don't waste time here
            elif 'age' in block:
                # otherwise increase its age
                block['age'] += 1
                _, oldest = oldest_blk
                if block['age'] > oldest:
                    # and keep track of the oldest block
                    oldest_blk = (blk_num, block['age'])

            # now check if that block contains this tag
            if 'tag' in block and block['tag'] == this_tag:
                # for both reads and writes
                # we record our findings
                found_or_replaced = cache_hit(True)
                # and reset its age
                block['age'] = 0

                # if this is a write
                if read_or_write == 'write':
                    # we update with new info
                    block['offset'] = this_offset
                    block['dirty'] = True

                    # and if it's a WT
                    # we update main memory
                    if write_thru:
                        # data changed, must write word through
                        cache_to_mem(4)
                        block['dirty'] = False

                continue  # end this iteration
                # don't break so that we may update all ages

        # if you made it here then
        # all blocks have been searched and
        # the tag was never found
        # or a mismatch was found
        if not found_or_replaced:
            # for both reads and writes:
            # we record our findings
            cache_miss(True)
            # and load the cache from memory
            mem_to_cache(2**num_offset_bits)

            # prepare the block index into which
            # the new data should be stored
            oldest_index, _ = oldest_blk
            if not empty_blocks:
                replace_blk_w_index = oldest_index
            else:
                replace_blk_w_index = empty_blocks[-1]

            evicted_blk = shelf[this_index][replace_blk_w_index]
            # first check if we're evicting an old block
            if 'dirty' in evicted_blk and evicted_blk['dirty'] is True:
                # block is dirty: push to main mem before overwriting
                cache_to_mem(2**num_offset_bits)

            # create the base of our new data object
            data_ob = {'age': 0,
                       'tag': this_tag,
                       'offset': this_offset}

            if write_thru:
                # HANDLING WT
                if read_or_write == 'read':
                    # no change, no need to write word through
                    pass
                elif read_or_write == 'write':
                    # data changed, must write word through
                    cache_to_mem(4)
            else:
                # HANDLING WB
                if read_or_write == 'read':
                    # no change, data is not dirty
                    data_ob.update({'dirty': False})
                elif read_or_write == 'write':
                    # data changed, must mark dirty
                    data_ob.update({'dirty': True})

            # finally placing this in the bookshelf
            shelf[this_index][replace_blk_w_index] = data_ob
        continue

    # instructions are complete, but before we can
    # end the program, we need to push any
    # dirty cache objects into main memory
    for each_set in shelf:
        for each_block in each_set:
            if 'dirty' in each_block and each_block['dirty'] is True:
                # must replace some dirty block
                cache_to_mem(2**num_offset_bits)
                each_block['dirty'] = False

    # return our results to be printed
    return (hit_counter, main_to_cache_bytes, cache_to_main_bytes)


# this is a helper fn to keep track of cache hits
def cache_hit(occurred):
    global hit_counter
    if not occurred:
        pass
    elif occurred is True:
        hit_counter += 1
    return True


# this is a helper fn to keep track of cache misses
def cache_miss(occurred):
    global miss_counter
    if not occurred:
        pass
    elif occurred is True:
        miss_counter += 1
    return True


# this is a helper fn to keep track of main mem updates
def cache_to_mem(byte_count):
    global cache_to_main_bytes
    cache_to_main_bytes += byte_count


# this is a helper fn to keep track of main mem retrievals
def mem_to_cache(byte_count):
    global main_to_cache_bytes
    main_to_cache_bytes += byte_count


# this is a helper fn to create the cache memory representation
def create_bookshelf(total_sz, blk_sz, n_way):

    # prepare our working variables
    num_blocks_in_set = n_way
    num_of_blocks = total_sz / blk_sz
    num_of_sets = num_of_blocks / n_way
    num_bytes_in_set = num_blocks_in_set * blk_sz
    n_offset = log2(blk_sz)
    n_index = log2(num_of_sets)
    n_tag = 32 - (n_index + n_offset)

    # create an empty bookshelf with preset shelving
    temp = [[] for i in range(int(num_of_sets))]
    data = list()
    for one_set in temp:
        one_set = [{} for i in range(int(num_blocks_in_set))]
        data.append(one_set)

    # record the bookshelf's statistics
    # because the bookshelf itself is too heavy to create
    bookshelf = {
        'num_sets':           int(num_of_sets),
        'num_blocks_per_set': int(num_blocks_in_set),
        'num_bytes_per_set':  int(num_bytes_in_set),
        "num_offset_bits":    int(n_offset),
        "num_index_bits":     int(n_index),
        "num_tag_bits":       int(n_tag),
        'data':               data  # this is the empty bookshelf
    }
    return bookshelf


# this is a helper function that converts our .trace into a list of tuples
def get_instructions(fn):
    try:
        f = open(fn, "r")
    except FileNotFoundError:
        print("There was no file named \"" + fn +
              "\" at the path provided. Try asking for --help.")
        return

    lines = list(f)
    f.close()
    instructions = list()
    for line in lines:
        line = line.replace('\n', '')
        read_or_write, address = line.split()
        instruction = (read_or_write, address)
        instructions.append(instruction)
    return instructions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=('\"simulate.py\" determines the cache efficiency, under '
                     'a variety of different settings, for some provided set '
                     'of test instructions.\n\n Test instructions should be '
                     'in the following format:\n read 0x02000006\n read '
                     '0x04000004\n write 0x02000007\n ... &c'
                     ),
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--input_file',
                        '-fi',
                        help=('the filename to be read for R/W instructions. '
                              'The default value (when no other value is '
                              'provided) is \'./test1.trace\''),
                        type=str,
                        default="test1.trace")

    parser.add_argument('--output_file',
                        '-fo',
                        help=('the filename to be written with the R/W '
                              'instruction results. The default value '
                              '(when no other value is provided) is '
                              '\'./test1.result\''),
                        type=str,
                        default="test1.result")

    main(parser.parse_args(sys.argv[1:]))
