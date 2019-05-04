#!/usr/bin/env python3
# simulate.py

import sys, argparse
from math import log2

hit_counter = 0
miss_counter = 0
cache_to_main_bytes = 0
main_to_cache_bytes = 0

# loop through each possible combination
def main(args):

    # pull in our (default) filename
    input_file = args.input_file
    output_file = args.output_file
    # grab all of the instructions from that file
    instructions = get_instructions(input_file)


    # create the file if it does not exist
    # clear the file if it already exists
    open(output_file, "w+").close()
    # prepare the file for appending
    f = open(output_file, "a")

    # define all possible settings for the cache
    cache_sizes = (1024, 4096, 65536, 131072)
    block_sizes = (8, 16, 32, 128)
    cache_placement_types = (("DM", 1), ("2W", 2), ("4W", 4), ("FA", 0))
    write_back_policies = (("WB",0), ("WT",1))

    for total_sz in cache_sizes:
      for blk_sz in block_sizes:
        for plcmt_type in cache_placement_types:

          codename, n_way = plcmt_type
          if codename is not "FA":
            pass
          else:
            n_way = total_sz / blk_sz

          for wb_policy in write_back_policies:
            # run the cache evaluator for each possible settings combo
            bookshelf = create_bookshelf(total_sz, blk_sz, n_way)
            # print(bookshelf)
            results = testing_bookshelf(bookshelf, wb_policy, instructions)
            #, wb_policy, instructions
            hit_count, m2c_byte_count, c2m_byte_count = results
            hit_percent = hit_count / len(instructions)
            hit_percent = round(hit_percent, 2)
            block_count = bookshelf['num_blocks_per_set']
            policy, _ = wb_policy

            print(str(total_sz) + "\t" + str(blk_sz) + "\t" + str(codename)
                + "\t" + str(policy) + "\t" + str(hit_percent) + "\t"
                + str(m2c_byte_count) + "\t" + str(c2m_byte_count) + "\t"
                + str(block_count),
                file=f)

            bookshelf.clear()
    f.close()

def testing_bookshelf(bookshelf, wb_policy, instructions):

    global hit_counter
    global miss_counter
    global cache_to_main_bytes
    global main_to_cache_bytes

    hit_counter = 0
    miss_counter = 0
    cache_to_main_bytes = 0
    main_to_cache_bytes = 0

    _, write_thru = wb_policy

    shelf = bookshelf['data']
    num_sets = bookshelf['num_sets']
    num_tag_bits = bookshelf['num_tag_bits']
    num_index_bits = bookshelf['num_index_bits']
    num_offset_bits = bookshelf['num_offset_bits']

    offset_mask = 2 ** num_offset_bits - 1;

    index_mask = 2 ** num_index_bits - 1;
    index_mask = index_mask << num_offset_bits

    tag_mask = 2 ** num_tag_bits - 1;
    tag_mask = tag_mask << (num_offset_bits + num_index_bits)

    for instruction in instructions:
        read_or_write, address = instruction
        # bit_address = bin(int(address, 16))[2:].zfill(32)
        bit_address = int(address, 16)

        this_offset = bit_address & offset_mask
        this_index = bit_address & index_mask
        this_tag = bit_address & tag_mask

        # print(read_or_write)
        if read_or_write == 'read':
          # print("reading", address)
          set_of_blks = shelf[this_index]
          # found the index
          empty_blocks = []
          oldest_blk = (0, 0)
          found_or_replaced = False
          for blk_num, block in enumerate(set_of_blks):
            # increase the age of every block we see
            if 'age' in block:
              # print("age increased")
              block['age'] += 1
              _, oldest = oldest_blk
              if block['age'] > oldest:
                oldest_blk = (blk_num, block['age'])
            # skip if the the block is empty
            elif not block:
              # block is empty
              empty_blocks.append(blk_num)
              continue # end this loop

            # check each block {} for this tag
            if 'tag' in block and block['tag'] == this_tag:
              # print("cache read hit")
              # tag match
              found_or_replaced = cache_hit(True)
              block['age'] = 0

              # if 'dirty' in block and block['dirty'] is True:
              #   # must replace some dirty block
              #   cache_to_mem(2**num_offset_bits)
              #   print("c2m")
              #   block['dirty'] = False

              continue # end this loop

          # tag not found or mismatch found
          if not found_or_replaced:
            cache_miss(True)
            # print("cache read miss")

            oldest_index, _ = oldest_blk
            if not empty_blocks:
              replace_blk_w_index = oldest_index
            else:
              replace_blk_w_index = empty_blocks[-1]

            mem_ob = {'tag':this_tag,
                    'offset':this_offset,
                    'age':0}

            old_blk = shelf[this_index][replace_blk_w_index]
            # write to memory before eviction
            if write_thru:
              pass
            elif 'dirty' in old_blk and old_blk['dirty'] is True:
              # must replace some dirty block
              cache_to_mem(2**num_offset_bits)
              mem_ob.update({'dirty':False})

            shelf[this_index][replace_blk_w_index] = mem_ob
            mem_to_cache(2**num_offset_bits)
            continue  # end this loop


        elif read_or_write == 'write':
          # print("writing", address)
          set_of_blks = shelf[this_index]
          # found the index
          empty_blocks = []
          oldest_blk = (0, 0)
          found_or_replaced = False
          for blk_num, block in enumerate(set_of_blks):
            # increase age of each block we see
            if 'age' in block:
              # print("age increased")
              block['age'] += 1
              _, oldest = oldest_blk
              if block['age'] > oldest:
                oldest_blk = (blk_num, block['age'])
            # skip if the block is empty
            elif not block:
              # block is empty
              empty_blocks.append(blk_num)
              continue # end this loop

            # check each block {} for this tag
            if 'tag' in block and block['tag'] == this_tag:
              # print("cache write hit")
              # tag match
              found_or_replaced = cache_hit(True)

              block['offset'] = this_offset
              block['age'] = 0

              if write_thru:
                cache_to_mem(2**num_offset_bits)
                block['dirty'] = False
              else:
                block['dirty'] = True
              continue # end this loop

          # tag not found or mismatch found
          if not found_or_replaced:
            cache_miss(True)
            # print("cache write miss")

            oldest_index, _ = oldest_blk
            if not empty_blocks:
              replace_blk_w_index = oldest_index
            else:
              replace_blk_w_index = empty_blocks[-1]

            # allocate on write
            mem_to_cache(2**num_offset_bits)
            temp = {'tag':this_tag,
                    'offset':this_offset,
                    'age':0}

            old_blk = shelf[this_index][replace_blk_w_index]
            # write to memory before eviction
            if write_thru:
              cache_to_mem(2**num_offset_bits)
            elif 'dirty' in old_blk and old_blk['dirty'] is True:
              # must replace some dirty block
              cache_to_mem(2**num_offset_bits)
              temp.update({'dirty':True})
            else:
              temp.update({'dirty':True})

            shelf[this_index][replace_blk_w_index] = temp
            continue  # end this loop

    # instructions are complete
    # before we end the program,
    # we need to push any dirty
    # cache into main memory
    for each_set in shelf:
      for each_block in each_set:
        if 'dirty' in each_block and each_block['dirty'] is True:
          # must replace some dirty block
          cache_to_mem(2**num_offset_bits)

    # print("hit_counter", "miss_counter", "main_to_cache_bytes", "cache_to_main_bytes")
    # print(hit_counter, miss_counter, main_to_cache_bytes, cache_to_main_bytes)

    return (hit_counter, main_to_cache_bytes, cache_to_main_bytes)

def cache_hit(occurred):
    global hit_counter
    if not occurred:
        pass
    elif occurred is True:
        hit_counter += 1
    return True

def cache_miss(occurred):
    global miss_counter
    if not occurred:
        pass
    elif occurred is True:
        miss_counter += 1
    return True

def cache_to_mem(byte_count):
    global cache_to_main_bytes
    cache_to_main_bytes += byte_count

def mem_to_cache(byte_count):
    global main_to_cache_bytes
    main_to_cache_bytes += byte_count

def create_bookshelf(total_sz, blk_sz, n_way):

    num_blocks_in_set = n_way
    num_of_blocks = total_sz / blk_sz
    num_of_sets = num_of_blocks / n_way
    num_bytes_in_set = num_blocks_in_set * blk_sz
    n_offset = log2(blk_sz)
    n_index = log2(num_of_sets)
    n_tag = 32 - (n_index + n_offset)

    temp = [ [] for i in range(int(num_of_sets)) ]
    data = list()
    for one_set in temp:
        one_set = [ {} for i in range(int(num_blocks_in_set)) ]
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
        'data':               data # this is the empty bookshelf
    }
    # print(bookshelf)
    return bookshelf


def get_instructions(fn):
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
    return instructions

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='\"simulate.py\" determines the cache efficiency, under a variety of different settings, for some provided set of test instructions.\n\n'+
        'Test instructions should be in the following format:\n'+
        'read 0x02000006\n'+
        'read 0x04000004\n'+
        'write 0x02000007\n'+
        '... &c', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--input_file',
                        '-fi',
                        help="the filename to be read for R/W instructions. The default value (when no other value is provided) is \'./test1.trace\'",
                        type=str,
                        default="test1.trace")

    parser.add_argument('--output_file',
                        '-fo',
                        help="the filename to be written with the R/W instruction results. The default value (when no other value is provided) is \'./test1.result\'",
                        type=str,
                        default="test1.result")

    main(parser.parse_args(sys.argv[1:]))