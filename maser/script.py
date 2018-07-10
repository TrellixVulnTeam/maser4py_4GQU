#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Main script program for maser4py."""

# ________________ IMPORT _________________________
# (Include here the modules to import, e.g. import sys)
import sys
import os
import argparse
import logging
from datetime import datetime

from ._version import __version__
from .utils.toolbox import setup_logging
from .utils.cdf.converter import skeletoncdf, SkeletonCDFException, add_skeletoncdf_subparser
from .utils.cdf.cdfcompare import cdf_compare, add_cdfcompare_subparser
from .utils.time import Lstable, add_leapsec_subparser

# ________________ HEADER _________________________


# ________________ Global Variables _____________
# (define here the global variables)
logger = logging.getLogger(__name__)

INPUT_DATE = "%Y-%m-%dT%H:%M:%S"

# ________________ Class Definition __________
# (If required, define here classes)


# ________________ Global Functions __________
# (If required, define here global functions)
def main():
    """Main program."""
    parser = argparse.ArgumentParser(add_help=True,
                                     description='MASER4PY application')
    parser.add_argument('--version', action='store_true',
                        help="Print MASER4PY version")
    parser.add_argument('-l', '--log-file', nargs=1,
                        default=[None],
                        help="log file path")
    parser.add_argument('-V', '--verbose',
                        action='store_true',
                        help="Verbose mode")
    parser.add_argument('-Q', '--quiet',
                        action='store_true',
                        help="Quiet mode")
    parser.add_argument('-D', '--debug',
                        action='store_true',
                        help="Debug mode")

    # Add maser subparsers
    subparsers = parser.add_subparsers(dest="maser",
                                          description='maser sub-commands')

    # Initializing subparsers
    add_skeletoncdf_subparser(subparsers)
    add_leapsec_subparser(subparsers)
    add_cdfcompare_subparser(subparsers)

    # Parse args
    args = parser.parse_args()

    # Setup the logging
    setup_logging(
        filename=args.log_file[0],
        quiet=args.quiet,
        verbose=args.verbose,
        debug=args.debug)

    if args.version:
        print("This is MASER4PY V{0}".format(__version__))
    elif args.maser is not None:
        # skeletoncdf sub-command
        if 'skeletoncdf' in args.maser:
            skeletons = args.skeletons
            nskt = len(skeletons)
            logger.info("{0} input file(s) found.".format(nskt))
            # Initializing list of bad conversion encountered
            bad_skt = []
            # Loop over the input skeleton files
            for i, skt in enumerate(args.skeletons):
                logger.info("Executing skeletoncdf for {0}... [{1}/{2}]".format(skt, i + 1, nskt))
                try:
                    cdf = skeletoncdf(skt,
                                      from_xlsx=args.excel_format,
                                      output_dir=args.output_dir[0],
                                      overwrite=args.overwrite,
                                      exe=args.skeletoncdf[0],
                                      ignore_none=args.ignore_none,
                                      auto_pad=args.auto_pad)
                except SkeletonCDFException as strerror:
                    logger.error("SkeletonCDF error -- {0}".format(strerror))
                    cdf = None
                except ValueError as strerror:
                    logger.error("Value error -- {0}".format(strerror))
                    cdf = None
                except:
                    logger.error(sys.exc_info()[0])
                    cdf = None
                finally:
                    if cdf is None:
                        bad_skt.append(skt)
                        logger.error("Converting {0} has failed, aborting!".format(skt))
                        if not args.force:
                            sys.exit(-1)

            if len(bad_skt) > 0:
                logger.warning("Following files have not been converted correctly:")
                for bad in bad_skt:
                    logger.warning(bad)
        # leapsec sub-command
        elif 'leapsec' in args.maser:
            # If get_file then download CDFLeapSeconds.txt file and exit
            if args.DOWNLOAD_FILE:
                target_dir = os.path.dirname(args.filepath[0])
                Lstable.get_lstable_file(target_dir=target_dir,
                                         overwrite=args.OVERWRITE)
                sys.exit()
            lst = Lstable(file=args.filepath[0])
            if args.date[0] is not None:
                date = datetime.strptime(args.date[0], INPUT_DATE)
                print("{0} sec.".format(lst.get_leapsec(date=date)))
            elif args.SHOW_TABLE:
                print(lst)
            else:
                parser.print_help()
                # leapsec sub-command
        # cdf_compare sub-command
        elif 'cdf_compare' in args.maser:
            cdfcompare = args.cdf_compare
            nargs = len(cdfcompare)
            if (nargs < 3 or nargs > 3):
                print('SYNTAX : cdf_compare cdf_file_path1 cdf_file_Path2')
            else:
                for file1, file2 in enumerate(args.cdf_compare):
                    try:
                        result = cdf_compare(file1, file2)
                    finally:
                        if result is None:
                            logger.error('CDF_COMPARE : Faillure !!!')
                            sys.exit(-1)

    else:
        parser.print_help()

    # _________________ Main ____________________________


if __name__ == "__main__":
    main()
