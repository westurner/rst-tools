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
                    (0, underline_char, "\n".join([overline, title, underline]), title_obj.start(), title_obj.end())
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
                (heading_level, underline_char, "\n".join((text, line)), g.start(), g.end())
            )
            # print heading_level,
            log.debug("%d\t%s%s" % (depth, heading_level * "   ", text))


def find_preceding_directives(text, start_index):
    """
    Search backwards from start_index for existing directives.
    Returns the start index of the preamble (including directives and blank lines).
    """
    idx = start_index
    while idx > 0:
        # Find start of the line ending at idx (meaning char at idx-1 is end of that line, likely \n)
        # Scan back for previous newline
        prev_newline = text.rfind('\n', 0, idx - 1 if idx > 0 and text[idx-1] == '\n' else idx)

        line_start = prev_newline + 1
        line_content = text[line_start:idx]

        stripped = line_content.strip()

        # Check if line is empty or a target directive
        if not stripped:
            idx = line_start
            continue

        if stripped.startswith('.. index::') or (stripped.startswith('.. _') and stripped.strip().endswith(':')):
             idx = line_start
             continue

        # Stop if we hit something else
        break
    return idx


def rst_shift(input_file, shiftby, shift_title=True, add_index=False, add_reference=False, no_leading_newlines=False, preserve_references=True):
    """

    Shift the headings of a restructuredtext document

    :param input_file: ReStructuredText file to read
    :type input_file: str
    :param shiftby: offset to shift headings by
    :type shiftby: signed int
    :param add_index: Add index directive
    :type add_index: bool
    :param add_reference: Add reference target
    :type add_reference: bool
    :param no_leading_newlines: Do not add leading newlines before directives
    :type no_leading_newlines: bool
    :param preserve_references: Preserve existing reference targets
    :type preserve_references: bool
    """

    if hasattr(input_file, 'read'):
         lines = input_file.read()
    else:
         lines = str(input_file) # fallback? existing code used open? assume read() works if passed as file.
         # The existing code did `f = input_file; lines = f.read()` but main passes arg directly?
         # If existing tests pass StringIO, then read() exists.
         # If older main used filename string, it would fail `f.read()` unless `f` is file.
         # I'll rely on `read()` being available or `input_file` being content string if not?
         # No, existing code: `lines = f.read()` implies f is file-like.
         pass

    # Check if lines is bytes (if opened 'rb'?) -> assume string.

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

    # Collect replacements to apply them in reverse order (to maintain indices)
    replacements = []

    # Perform underline replacements
    for section in sections:
        (depth, char, text, start, end) = section
        newdepth = depth + shiftby
        newchar = headings_by_n[newdepth]
        newtext = None

        section_part, underline = text.split("\n", 1)

        # special case for title header
        if shiftby != 0:
            if depth == 0 and len(char) > 1:
                char = char[0]
                newchar = newchar[0]
                if shiftby > 0:
                    section_part = ""
            elif depth == 1 and text.startswith("\n"):
                newtext = "\n"

        newtext = newtext or "\n".join((section_part, underline.replace(char, newchar)))
        newtext += "\n"

        replace_start = start
        replace_end = end

        # Handle add_index and add_reference insertions / updates
        if add_index or add_reference:
             # Look for preceding directives
             p_start = find_preceding_directives(lines, start)
             if p_start < start:
                 replace_start = p_start

             # Extract title string
             if depth == 0:
                 # text: Overline\nTitle\nUnderline
                 parts = text.split('\n')
                 title_str = parts[1].strip() if len(parts) > 1 else ""
             else:
                 # text: Title\nUnderline
                 parts = text.split('\n')
                 title_str = parts[0].strip()

             directives = []
             if add_index:
                 directives.append(f".. index:: {title_str}")

             if add_reference:
                 # Slugify: lowercase, replace non-alphanumeric with hyphens
                 slug = re.sub(r'[\W_]+', '-', title_str.lower()).strip('-')
                 new_ref = f".. _{slug}:"

                 existing_refs = []
                 if preserve_references and replace_start < start:
                     # Parse existing block for references
                     existing_block = lines[replace_start:start]
                     for line in existing_block.split('\n'):
                         sline = line.strip()
                         # We only preserve references that look valid
                         if sline.startswith('.. _') and sline.endswith(':'):
                             existing_refs.append(sline)

                 if new_ref not in existing_refs:
                     existing_refs.append(new_ref)

                 directives.extend(existing_refs)

             if directives:
                 prefix = '\n'.join(directives) + '\n\n'
                 if not no_leading_newlines and replace_start > 0:
                     prefix = "\n\n" + prefix
                 newtext = prefix + newtext

        log.debug((depth, newdepth, text, newtext))
        replacements.append((replace_start, replace_end, newtext))

    # Apply replacements
    replacements.sort(key=lambda x: x[0], reverse=True)
    output = lines
    for start, end, chunk in replacements:
        output = output[:start] + chunk + output[end:]

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

_RST_TEST_OUTPUT_1_ADD_OPTS = """
.. index:: Title
.. _title:

=====
Title
=====
title_content


.. index:: Heading 1
.. _heading-1:

Heading 1
=========


.. index:: Heading 1.1
.. _heading-1-1:

Heading 1.1
-----------


.. index:: Heading 1.1.1
.. _heading-1-1-1:

Heading 1.1.1
~~~~~~~~~~~~~


.. index:: Heading 2
.. _heading-2:

Heading 2
=========
"""

# Output without leading newlines (for --no-add-leading-newlines test)
_RST_TEST_OUTPUT_1_ADD_OPTS_NO_NL = """
.. index:: Title
.. _title:

=====
Title
=====
title_content
.. index:: Heading 1
.. _heading-1:

Heading 1
=========
.. index:: Heading 1.1
.. _heading-1-1:

Heading 1.1
-----------
.. index:: Heading 1.1.1
.. _heading-1-1-1:

Heading 1.1.1
~~~~~~~~~~~~~
.. index:: Heading 2
.. _heading-2:

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

    def test_rst_add_opts(self):
        input_ = StringIO(_RST_TEST_INPUT_1)
        output = rst_shift(input_, 0, add_index=True, add_reference=True)
        # Note: The expected output includes the prepended index/refs, BUT rst_shift replaces text.
        # Since rst_shift currently only finds sections, if there are multiple sections, it inserts for each.
        # Let's compare against constructed expected output
        try:
             # Basic check to see if directives are present
             self.assertIn(".. index:: Title", output)
             self.assertIn(".. _heading-1-1:", output)
             self.assertEqual(output.strip(), _RST_TEST_OUTPUT_1_ADD_OPTS.strip())
        except Exception:
             print("Output:\n" + output)
             print("Expected:\n" + _RST_TEST_OUTPUT_1_ADD_OPTS)
             raise

    def test_rst_add_opts_no_nl(self):
        input_ = StringIO(_RST_TEST_INPUT_1)
        output = rst_shift(input_, 0, add_index=True, add_reference=True, no_leading_newlines=True)
        try:
             self.assertIn(".. index:: Title", output)
             self.assertEqual(output.strip(), _RST_TEST_OUTPUT_1_ADD_OPTS_NO_NL.strip())
        except Exception:
             print("Output:\n" + output)
             print("Expected:\n" + _RST_TEST_OUTPUT_1_ADD_OPTS_NO_NL)
             raise

    def test_rst_multiple_references_preservation(self):
        input_str = """
.. index:: Multi
.. _multi:
.. _alias1:
.. _alias2:

Multi Title
===========
"""
        # Default behavior: preserve_references=True
        input_ = StringIO(input_str)
        output = rst_shift(input_, 0, add_index=True, add_reference=True)

        # New "slug" ref should be _multi-title:
        # Expected:
        # .. index:: Multi Title
        # .. _multi-title:
        # .. _alias1:
        # .. _alias2:
        #
        # Multi Title
        # ===========

        self.assertIn(".. index:: Multi Title", output)
        self.assertIn(".. _multi-title:", output)
        self.assertIn(".. _alias1:", output)
        self.assertIn(".. _alias2:", output)

        # Check that old '.. _multi:' (if not same as new one) is also preserved?
        # Yes, logic preserves all valid refs found in the block.
        self.assertIn(".. _multi:", output)

        # Test with no-preserve
        input_ = StringIO(input_str)
        output = rst_shift(input_, 0, add_index=True, add_reference=True, preserve_references=False)
        self.assertIn(".. index:: Multi Title", output)
        self.assertIn(".. _multi-title:", output)
        # Aliases should be gone because we overwrite full block with just new directives
        self.assertNotIn(".. _alias1:", output)
        self.assertNotIn(".. _alias2:", output)


    def test_rst_update_opts(self):
        # Input with old directives that should be replaced
        input_str = """
.. index:: Old
.. _old:

Title
=====
"""
        input_ = StringIO(input_str)
        # We rely on preserve_references=False to clean up old refs
        output = rst_shift(input_, 0, add_index=True, add_reference=True, preserve_references=False)

        expected = """
.. index:: Title
.. _title:

Title
=====
"""
        # Note: rst_shift output might contain leading newlines if input did or if we added them.
        # Our update logic replaces [p_start:end].
        # p_start includes ".. index:: Old\n".
        # If input starts with newline, p_start might range.
        # The output logic adds '\n\n' after directives.
        # So: .. index:: Title\n.. _title:\n\nTitle\n=====\n

        self.assertIn(".. index:: Title", output)
        self.assertIn(".. _title:", output)
        self.assertNotIn(".. index:: Old", output)
        self.assertNotIn(".. _old:", output)
        self.assertEqual(output.strip(), expected.strip())


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
    prs.add_argument(
        "--add-index",
        dest="add_index",
        action="store_true",
        help="Add '.. index:: {title}' directive above sections."
    )
    prs.add_argument(
        "--add-reference",
        dest="add_reference",
        action="store_true",
        help="Add '.. _{slugified_title}:' target above sections."
    )
    prs.add_argument(
        "--no-add-leading-newlines",
        dest="no_leading_newlines",
        action="store_true",
        help="Disable adding 2 newlines before directives when using --add-index."
    )
    prs.add_argument(
        "--no-preserve-references",
        dest="preserve_references",
        action="store_false",
        default=True,
        help="Do not preserve existing reference targets that are not being added."
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
        output = rst_shift(
            input_stream,
            int(opts.shiftby),
            add_index=opts.add_index,
            add_reference=opts.add_reference,
            no_leading_newlines=opts.no_leading_newlines,
            preserve_references=opts.preserve_references
        )

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
