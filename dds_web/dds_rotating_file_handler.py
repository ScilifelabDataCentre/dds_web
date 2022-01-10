"""DDSRotatingFileHandler for handling the execution, formatting and rotation of logging files."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import logging
import pathlib

# Installed

# Own modules

# CLASSES ################################################################################ CLASSES #


class DDSRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(
        self,
        filename,
        basedir,
        mode="a",
        maxBytes=1e9,
        backupCount=0,
        encoding=None,
        delay=0,
    ):
        """
        Custom RotatingFileHandler, logs to the file `<basedir>/<filename>.log`
        and renames the current file to `<basedir>/<filename>_[timestamp].log` when the file size
        reaches <maxBytes> --> Current logging always to <filename>.log.
        """

        self.today_ = datetime.datetime.utcnow() if not hasattr(self, "today_") else self.today_
        self.basedir_ = pathlib.Path(basedir)  # Log directory
        self.basename = pathlib.Path(filename)  # Base for all filenames
        self.active_file_name = self.basedir_ / self.basename.with_suffix(".log")  # Active file

        # Initiate super class
        logging.handlers.RotatingFileHandler.__init__(
            self, self.active_file_name, mode, maxBytes, backupCount, encoding, delay
        )

    def shouldRollover(self, record):
        """
        Checks if the FileHandler should do a rollover of the log file.
        """

        if self.stream is None:
            self.stream = self._open()

        # Check if the file is at max size
        if self.maxBytes > 0:
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)
            if self.stream.tell() + len(msg) >= self.maxBytes:
                # Create time stamp and rename the current log file to contain rollover timestamp
                new_today = datetime.datetime.utcnow()
                replacement_name = pathlib.Path(
                    str(self.basename)
                    + "_"
                    + self.today_.strftime("%Y-%m-%d-%H-%M-%S")
                    + "_"
                    + new_today.strftime("%Y-%m-%d-%H-%M-%S")
                    + ".log"
                )
                self.active_file_name.rename(target=pathlib.Path(self.basedir_ / replacement_name))
                self.today_ = new_today
                return 1

        return 0
