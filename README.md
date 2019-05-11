# Program: Simulate.py
# Author: Ben Shaker
# Date: May 2019

## Purpose

simulate.py is a cache memory simulator that facilitates the simple comparison of many possible cache arrangements. It feeds pre-recorded memory instructions ('reads' & 'writes' for particular 32-bit memory addresses) through a simulator which mimics, in total, 128 different cache memory setups - each of which is slightly different than the last. The full list of cache settings is printed here:

Cache Size (in bytes): ["1K", "4K", "64K", "128K"]
Block Size (in bytes): ["8", "16", "32", "128"]
Cache Placement Type: ["Direct Mapped", "2-way set associative", "4-way set associative", "Fully associative"]
Write Policy: ["Write-back", "Write-through"]

Each potential combination of these settings (4*4*4*2 = 128) gives us an individual cache to simulate. Once each simulation has completed, then those results are stored in the provided output file. This file tries to be very readable in its output format. It has eight columns which can be read as follows:

1) Cache size
2) Block size
3) Cache Placement Type
4) Write policy
5) Hit rate (as a percentage)
6) Total bytes transferred from memory to the cache
7) Total bytes transferred from cache to memory
8) Number of blocks within each set

## Installation

The file simulate.py was written on a system running macOS Mojave and it was constructed using only the terminal (command line) and a simple text editor (Sublime Text 2).

To envoke simulate.py, simply run that same Python file from your own terminal (command line).
Note that simulate.py was built using Python 3.7 and it assumes your system is also capable of running code in that environment. You will likely encounter unknown issues attempting to run this program under earlier Python versions, especially any version of Python 2. Simple modifications could be made, however, to give this program backwards-compatiblitity.

You may need to import one or more additional libraries before being able to run simulate.py. The full list of libraries we use is: ["sys","argparse","math"] One common way to install new libraries locally are the commands 'pip install' (for systems defaulting to Python 3) and 'pip3 install' (for systems with both Python 2 & Python 3 installed). The specific details of envoking your library installer may differ. Here is one common way to install a required library:

```pip3 install argparse```


## Usage

simulate.py allows for two optional arguments, and they are:

1) ```--input_file (a.k.a. -fi)```

some example evocations:
```simulate.py --input_file test1.trace
simulate.py -fi test1.trace```

where the input file provided is the full (i.e. file type is also necessary) filename that will be read from to gather read/write instructions. The program should error gracefully when no input file is found at the provided file location.

and

2) ```--output_file (a.k.a. -fo)```

some example evocations:
```simulate.py --output_file test1.result
simulate.py -fo test1.result```

where the output file provided is the full (i.e. file type is also necessary) filename that will store the output of the various cache simulations. The program should create the file when it does not already exist, and it should empty the file if it does already exist (so that the simulators new results are not confused with any old results).

If no input or output filenames are designated then the system will default to the values indicated in the examples above.


## Contact

For questions or comments feel free to reach out to the author: bshaker@vt.edu
Thanks!
