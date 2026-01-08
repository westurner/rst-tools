#!/usr/bin/env python3
# encoding: utf-8
"""
ReStructuredText Utility for modifying ReStructuredText headings by the
specified shift offset.

"""

import itertools
import logging
import argparse
import re
import sys
import unittest
import unittest.mock
from collections import namedtuple, OrderedDict
from io import StringIO

RGX_TITLE = re.compile(r"^([\=|\-|\~]+)\n(.*)\n^([\=|\-|\~]+)\n", re.MULTILINE)
RGX_HEADING = re.compile(
    r"^(?:[\=|\-|\~]?)(?:[\n]?)(.*)\n^([\=|\-|\~]+)\n", re.MULTILINE
)


RGX_TITLE = re.compile(r"^([\=|\-|\~]+)\n(.*)\n^([\=|\-|\~]+)\n", re.MULTILINE)
RGX_HEADING = re.compile(
    r"^(?:[\=|\-|\~]?)(?:[\n]?)(.*)\n^([\=|\-|\~]+)\n", re.MULTILINE
)

STANDARD_HEADINGS = OrderedDict(
    (
        (0, "=="),
        (1, "="),
        (2, "-"),
        (3, "~"),
        (4, "'"),
        (5, '"'),
        (6, "`"),
        (7, "^"),
        (8, "_"),
        (9, "*"),
        (10, "+"),
        (11, "#"),
        (12, "<"),
        (13, ">"),
    )
)

log = logging.getLogger()


class RstParser(object):
    def __init__(self, source):
        self.source = source
        self.headings = OrderedDict()
        self.sections = []
        self.depthcount = 0
        self.title_text = None
        self.parse()

    def parse(self):
        lines = self.source

        # Special case for title
        title_obj = RGX_TITLE.search(lines)

        (overline, title, underline) = ("=", "", "=")
        title = None
        if title_obj:
            (overline, title, underline) = title_obj.groups()
            self.title_text = title
            if not len(overline) == len(underline):
                log.error((overline, title, underline))
                raise Exception("is this a malformed title?")
            else:
                underline_char = overline[0] * 2  # Because it is a header
                self.headings[underline_char] = 0
                log.debug("document headings: %s" % self.headings)
                log.debug(title)
                log.debug("%d\t%s%s" % (0, 0 * "   ", title))
                self.sections.append(
                    (0, underline_char, "\n".join([overline, title, underline]))
                )

        # Extract section headings and existing section heading numbering
        # for each heading in the document
        for g in RGX_HEADING.finditer(lines):
            (text, line) = g.groups()
            if self.title_text and text in self.title_text and line == underline:
                continue  # TODO
            underline_char = line[0]
            # check if this heading type is already in the document
            depth = self.headings.get(underline_char)
            if not depth:
                self.depthcount += 1
                self.headings[underline_char] = self.depthcount
                depth = self.depthcount
            # log.debug(depth)

            heading_level = self.headings[underline_char]
            self.sections.append(
                (heading_level, underline_char, "\n".join((text, line)))
            )
            # print heading_level,
            log.debug("%d\t%s%s" % (depth, heading_level * "   ", text))


def rst_shift(input_file, shiftby, shift_title=True):
    """

    Shift the headings of a restructuredtext document

    :param input_file: ReStructuredText file to read
    :type input_file: str
    :param shiftby: offset to shift headings by
    :type shiftby: signed int
    """

    f = input_file  # open(input_file,'r+')
    lines = f.read()

    parser = RstParser(lines)
    headings = parser.headings
    sections = parser.sections
    depthcount = parser.depthcount

    log.debug("document headings: %s" % headings)

    STD_HEADINGS = list(STANDARD_HEADINGS.values())

    log.debug(" ".join(STD_HEADINGS))

    current_depth_counter = depthcount + 1
    used_chars = set(headings.keys())

    for char in STD_HEADINGS:
        if char not in used_chars:
            headings[char] = current_depth_counter
            current_depth_counter += 1

    headings_by_n = {v: k for k, v in headings.items()}

    log.debug("document headings: %s" % headings)
    log.debug(" ".join(STD_HEADINGS))
    log.debug(" ".join(str(x) for x in headings_by_n.values()))

    # TODO

    # output = copy.copy(lines)
    output = lines

    # Perform underline replacements
    for section in sections:
        (depth, char, text) = section
        newdepth = depth + shiftby
        newchar = headings_by_n[newdepth]
        newtext = None

        section, underline = text.split("\n", 1)

        # special case for title header
        if shiftby != 0:
            if depth == 0 and len(char) > 1:
                char = char[0]
                newchar = newchar[0]
                if shiftby > 0:
                    section = ""
            elif depth == 1 and text.startswith("\n"):
                newtext = "\n"

        newtext = newtext or "\n".join((section, underline.replace(char, newchar)))

        log.error((depth, newdepth, text, newtext))
        output = output.replace(text, newtext, 1)

    return output


_TestCase = namedtuple(
    "_TestCase",
    (
        "input",
        "shiftkey",
        "output",
    ),
)

# (input,

_RST_TEST_INPUT_1 = """
=====
Title
=====
title_content
Heading 1
=========
Heading 1.1
-----------
Heading 1.1.1
~~~~~~~~~~~~~
Heading 2
=========
"""

RST_TESTS = (
    _TestCase(_RST_TEST_INPUT_1, 0, _RST_TEST_INPUT_1),
    _TestCase(
        _RST_TEST_INPUT_1,
        1,
        """

Title
=====
title_content
Heading 1
---------
Heading 1.1
~~~~~~~~~~~
Heading 1.1.1
'''''''''''''
Heading 2
---------
""",
    ),
)

# RST_TEST_DICT = OrderedDict(
#    ((t.input,t.shiftkey), t.output) for t in RST_TESTS
# )


def _compare_test_output(_input, _output, expected_output):
    formatstr = "%-20s %-20s %-20s"

    log.error(formatstr % ("input", "output", "expected output"))
    log.error("=" * 60)
    for n in itertools.zip_longest(
        _input.split("\n"), _output.split("\n"), expected_output.split("\n")
    ):
        log.error(formatstr % (n))




class Test_rst_shift(unittest.TestCase):
    def test_rst_1(self):
        for test_input, shift, expected_output in RST_TESTS:
            input_ = StringIO(test_input)
            output = rst_shift(input_, shift)
            try:
                self.assertEqual(expected_output, output)
            except Exception as e:
                log.exception(e)
                log.error("# shift = %r" % shift)
                _compare_test_output(test_input, output, expected_output)
                raise

class Test_RstParser(unittest.TestCase):
    def test_parse_simple(self):
        input_ = _RST_TEST_INPUT_1
        parser = RstParser(input_)
        self.assertEqual(len(parser.sections), 5) # Title + 4 sections
        # Check headings map
        # Title '==' -> 0 (parsed specialized)
        # Heading 1 '=' -> 1
        # Heading 1.1 '-' -> 2
        # Heading 1.1.1 '~' -> 3
        
        # '==' is stored as '==' for title? 
        # In parser: underline_char = overline[0]*2
        self.assertEqual(parser.headings['=='], 0) 
        self.assertEqual(parser.headings['='], 1)
        self.assertEqual(parser.headings['-'], 2)
        self.assertEqual(parser.headings['~'], 3)
        
        # Heading 2 '=' -> reused depth 1.
        
    def test_parse_no_title(self):
        input_ = """
Heading 1
=========
"""
        parser = RstParser(input_)
        self.assertEqual(len(parser.sections), 1)
        self.assertEqual(parser.headings['='], 1)

    def test_malformed_title(self):
        input_ = """
======
Title
=====
"""
        with self.assertRaises(Exception) as cm:
            RstParser(input_)
        self.assertIn("malformed title", str(cm.exception))


class Test_Main(unittest.TestCase):
    def test_main_help(self):
        # Test that --help exits cleanly (SystemExit)
        with unittest.mock.patch('sys.argv', ['rst_shift.py', '--help']):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    def test_main_process(self):
        # Run main with actual input
        with unittest.mock.patch('sys.argv', ['rst_shift.py', '-i', '-', '-s', '1']):
            with unittest.mock.patch('sys.stdin', StringIO(_RST_TEST_INPUT_1)):
                with unittest.mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    main()
                    self.assertNotEqual(mock_stdout.getvalue(), "")

    def test_main_missing_args(self):
         # Run without arguments. Expect help print and exit(1)
         with unittest.mock.patch('sys.argv', ['rst_shift.py']):
             with self.assertRaises(SystemExit) as cm:
                 main()
             self.assertEqual(cm.exception.code, 1)

    def test_main_file_io(self):
        # Test usage with actual file paths (mocked)
        with unittest.mock.patch('sys.argv', ['rst_shift.py', '-i', 'in.rst', '-o', 'out.rst', '-s', '1']):
             with unittest.mock.patch('builtins.open', unittest.mock.mock_open(read_data=_RST_TEST_INPUT_1)) as mock_file:
                 main()
                 # check open calls
                 # 1. open input 'in.rst' 'r+'
                 # 2. open output 'out.rst' 'w'
                 self.assertTrue(mock_file.call_count >= 2)
                 # Verify write to output
                 handle = mock_file()
                 self.assertTrue(handle.write.called)

class Test_Comparison(unittest.TestCase):
    def test_compare_output(self):
        # Call _compare_test_output directly to cover it
        with self.assertLogs(level='ERROR') as cm:
            _compare_test_output("a\nb", "a\nc", "a\nb")
        self.assertTrue(len(cm.output) > 0)


def main():

    prs = argparse.ArgumentParser(
        usage="%(prog)s : -s <int> -i <input_file> -o <output_file>",
        description="Shift reStructuredText headings by -s",
    )

    prs.add_argument(
        "-s",
        "--shiftby",
        dest="shiftby",
        action="store",
        default=0,
        help="Heading shift factor (-5, 5)",
    )
    prs.add_argument(
        "-i",
        "--input-file",
        dest="input_file",
        action="store",
        help="Input ReStructuredText file to shift headings",
    )
    prs.add_argument(
        "-o",
        "--output-file",
        dest="output_file",
        action="store",
        default=sys.stdout,
        help="Output file to shift headings",
    )

    prs.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="Show debugging output",
    )
    prs.add_argument(
        "-q", "--quiet", dest="quiet", action="store_true", help="Disable logging"
    )
    prs.add_argument(
        "-t", "--test", dest="run_tests", action="store_true", help="Run unit tests."
    )

    opts, args = prs.parse_known_args()

    if not opts.quiet:
        logging.basicConfig()

        if opts.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    if opts.run_tests:

        sys.argv = [sys.argv[0]] + args
        import subprocess
        subprocess.call([sys.executable, '-m', 'pytest', *args, __file__])
        #import unittest
        #exit(unittest.main())

    opts, args = prs.parse_known_args()

    # Logic to ensure we have necessary args.
    # If shiftby != 0, we MUST have input_file.
    # If shiftby == 0, we basically do nothing or just pass through?
    # Actually if input_file is missing, we fall through to print_help.
    if not (opts.input_file or opts.shiftby == 0):
         # If input_file is missing and shiftby != 0
         pass
    
    input_stream = None
    if opts.input_file == "-":
        input_stream = sys.stdin
    elif opts.input_file:
        input_stream = open(opts.input_file, "r+")
    
    if input_stream:
        output = rst_shift(input_stream, int(opts.shiftby))
        
        if opts.output_file is sys.stdout:
             opts.output_file.write(output)
        else:
             with open(opts.output_file, 'w') as f:
                 f.write(output)
    else:
        if args:
            log.error("Could not parse commandline arguments: %r" % args)
        prs.print_help()
        exit(1)


if __name__ == "__main__":
    main()
