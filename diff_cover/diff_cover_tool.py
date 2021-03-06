from __future__ import unicode_literals

import logging

import os
import sys
import argparse
import six

from xml.etree import cElementTree

from diff_cover import DESCRIPTION
from diff_cover.diff_reporter import GitDiffReporter
from diff_cover.git_diff import GitDiffTool
from diff_cover.git_path import GitPathTool
from diff_cover.report_generator import HtmlReportGenerator, StringReportGenerator
from diff_cover.violationsreporters.violations_reporter import XmlCoverageReporter

HTML_REPORT_HELP = "Diff coverage HTML output"
COMPARE_BRANCH_HELP = "Branch to compare"
CSS_FILE_HELP = "Write CSS into an external file"
FAIL_UNDER_HELP = "Returns an error code if coverage or quality score is below this value"
IGNORE_STAGED_HELP = "Ignores staged changes"
IGNORE_UNSTAGED_HELP = "Ignores unstaged changes"
EXCLUDE_HELP = "Exclude files, more patterns supported"
SRC_ROOTS_HELP = "List of source directories (only for jacoco coverage reports)"
COVERAGE_XML_HELP = "XML coverage report"

LOGGER = logging.getLogger(__name__)


def parse_coverage_args(argv):
    """
    Parse command line arguments, returning a dict of
    valid options:

        {
            'coverage_xml': COVERAGE_XML,
            'html_report': None | HTML_REPORT,
            'external_css_file': None | CSS_FILE,
        }

    where `COVERAGE_XML`, `HTML_REPORT`, and `CSS_FILE` are paths.

    The path strings may or may not exist.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument(
        'coverage_xml',
        type=str,
        help=COVERAGE_XML_HELP,
        nargs='+'
    )

    parser.add_argument(
        '--html-report',
        metavar='FILENAME',
        type=str,
        default=None,
        help=HTML_REPORT_HELP
    )

    parser.add_argument(
        '--external-css-file',
        metavar='FILENAME',
        type=str,
        default=None,
        help=CSS_FILE_HELP,
    )

    parser.add_argument(
        '--compare-branch',
        metavar='BRANCH',
        type=str,
        default='origin/master',
        help=COMPARE_BRANCH_HELP
    )

    parser.add_argument(
        '--fail-under',
        metavar='SCORE',
        type=float,
        default='0',
        help=FAIL_UNDER_HELP
    )

    parser.add_argument(
        '--ignore-staged',
        action='store_true',
        default=False,
        help=IGNORE_STAGED_HELP
    )

    parser.add_argument(
        '--ignore-unstaged',
        action='store_true',
        default=False,
        help=IGNORE_UNSTAGED_HELP
    )

    parser.add_argument(
        '--exclude',
        metavar='EXCLUDE',
        type=str,
        nargs='+',
        help=EXCLUDE_HELP
    )

    parser.add_argument(
        '--src-roots',
        metavar='DIRECTORY',
        type=str,
        nargs='+',
        default=['src/main/java', 'src/test/java'],
        help=SRC_ROOTS_HELP
    )

    return vars(parser.parse_args(argv))


def generate_coverage_report(coverage_xml, compare_branch,
                             html_report=None, css_file=None,
                             ignore_staged=False, ignore_unstaged=False,
                             exclude=None, src_roots=None):
    """
    Generate the diff coverage report, using kwargs from `parse_args()`.
    """
    diff = GitDiffReporter(
        compare_branch, git_diff=GitDiffTool(), ignore_staged=ignore_staged,
        ignore_unstaged=ignore_unstaged, exclude=exclude)

    xml_roots = [cElementTree.parse(xml_root) for xml_root in coverage_xml]
    coverage = XmlCoverageReporter(xml_roots, src_roots)

    # Build a report generator
    if html_report is not None:
        css_url = css_file
        if css_url is not None:
            css_url = os.path.relpath(css_file, os.path.dirname(html_report))
        reporter = HtmlReportGenerator(coverage, diff, css_url=css_url)
        with open(html_report, "wb") as output_file:
            reporter.generate_report(output_file)
        if css_file is not None:
            with open(css_file, "wb") as output_file:
                reporter.generate_css(output_file)

    reporter = StringReportGenerator(coverage, diff)
    output_file = sys.stdout if six.PY2 else sys.stdout.buffer

    # Generate the report
    reporter.generate_report(output_file)
    return reporter.total_percent_covered()


def main(argv=None, directory=None):
    """
       Main entry point for the tool, used by setup.py
       Returns a value that can be passed into exit() specifying
       the exit code.
       1 is an error
       0 is successful run
   """
    logging.basicConfig(format='%(message)s')

    argv = argv or sys.argv
    arg_dict = parse_coverage_args(argv[1:])
    GitPathTool.set_cwd(directory)
    fail_under = arg_dict.get('fail_under')
    percent_covered = generate_coverage_report(
        arg_dict['coverage_xml'],
        arg_dict['compare_branch'],
        html_report=arg_dict['html_report'],
        css_file=arg_dict['external_css_file'],
        ignore_staged=arg_dict['ignore_staged'],
        ignore_unstaged=arg_dict['ignore_unstaged'],
        exclude=arg_dict['exclude'],
        src_roots=arg_dict['src_roots'],
    )

    if percent_covered >= fail_under:
        return 0
    else:
        LOGGER.error("Failure. Coverage is below {}%.".format(fail_under))
        return 1


if __name__ == '__main__':
    sys.exit(main())
