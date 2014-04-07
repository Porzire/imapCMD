#!/usr/bin/env python -O

import argparse
import client
from getpass import getpass
from util import printd, printe

# Set welcome information.
WELCOME = 'Welcome using IMAP cmd.\n' +\
          'Only limited command with limited function is implemented for now.\n' + \
          'IMAP4 use \'/\' as file seperator.\n'

class Error(Exception): pass

# CommandError occurs when incorrect command received.
class CommandError(Error):
    def __init__(self, command, message, prefix='imapCMD: '):
        super(Error, self).__init__(prefix + command + ': ' + message)

class Cmd(object):
    """ This class provide user interface and define UNIX like command.

    It deal with user input, format and print out required data. It builds the
    user command with high-level function from client.py.

    Arguements:
        client: The IMAP client object.
        curr:   The current working directory.
    """

    def __init__(self, host=None, username=None, password=None):
        """ Initialize the client with connect established.

        Args:
            host:     The address of the IMAP SSL host.
            username: The username.
            password: The password.
        """
        if not host:     host = raw_input('host: ')
        if not username: username = raw_input('username: ')
        if not password: password = getpass()
        printd('Login information: ' + host + ' ' + username + ' ' + password)
        self.client = client.IMAPClient(host, username, password)
        self.curr = ''
        print(WELCOME)
        print('Login to ' + host + '.\n')
        while 1:
            command = raw_input(username + '$ ').lstrip().split(' ')
            try:
                # Avoid accessing private methods.
                if len(command[0]) > 0:
                    if command[0][0] == '_':
                        raise CommandError(command[0], 'command not found')
                    try:
                        getattr(self, command[0])(*command[1:])
                    except AttributeError:
                        raise CommandError(command[0], 'command not found')
                    except TypeError:
                        raise CommandError(command[0], 'command with invalid parameters')
            except CommandError, e:
                printe(e)

    def pwd(self):
        """ Get current working directory.
        """
        print('\\' + self.curr)

    def exit(self):
        """ Exit the program.
        """
        self.logout()

    def logout(self):
        """ Logout connection.
        """
        self.client.logout()
        print('IMAP4 connection closed.')
        sys.exit(0)

    def ls(self):
        """ list the subdirectories in the current working directory.
        """
        # Hide multiple level folder names.
        mailboxs = []
        for mbox in self._ls():
            if len(self.curr) != 0:
                mbox = mbox[len(self.curr) + 1:]
            pos = mbox.rfind('/')
            mbox = mbox[:pos] if pos > 0 else mbox
            if mbox not in mailboxs:
                mailboxs.append(mbox)
        print('\t'.join(mailboxs))

    def _ls(self):
        """ Return a list of mailbox.
        """
        # Get the mailbox list.
        directory = '""' if len(self.curr) == 0 else self.curr + '/'
        mailboxs = self.client.getMailBoxs(directory)
        return mailboxs

    def _path(self):
        """ Return the path safily for message retrieval.
        """
        return '""' if len(self.curr) == 0 else self.curr

    def lm(self):
        """ list the number of mails in the current working directory.
        """
        # Get the email uids.
        # In low-level, use FETCH instead of just SELECT, because EXIST is not
        # mandatory information and mailbox can receive new email after SELECT.
        num = len(self.client.getEmails(self._path()))
        to = num - 10 if num >= 10 else 1
        emails = self.client.getEmails(self._path(), '(RFC822.HEADER.LINES (Subject))', str(num) + ':' + str(to))
        print('emails(' + str(num) + ')')

    def cat(self, num):
        """ display the emil in the current working directory with mail id num.
        """
        head, body = self.client.getEmail(self._path(), num)
        print(head + '\n\n' + body)

    def cd(self, path):
        """ access the directory path. Step back to the parent directory if
        'path' is '..'.
        """
        # Only deal with first parameter (same as UNIX).
        if type(path) == type([]):
            path = path[0]
        # Step back.
        if path == '..':
            if self.curr != '""':
                pos = self.curr.rfind('/')
                if pos > 0:
                    self.curr = self.curr[:pos]
                else:
                    self.curr = ''
        # Step into folder.
        else:
            mailboxs = self._ls()
            # If given an absolute path.
            if path[0] == '/':
                if path[1:] in mailboxs:
                    self.curr = path[1:]
                else:
                    raise CommandError('ls', 'No such directory', '')
            else:
                path = ('' if len(self.curr) == 0 else self.curr + '/') + path
                if path in mailboxs:
                    self.curr = path
                else:
                    raise CommandError('ls', 'No such directory', '')

    def pwd(self):
        """ display the current working directory.
        """
        if self.curr == '""':
            print('/')
        else:
            print('/' + self.curr.replace('.', '/'))

    def mkdir(self, *paths):
        """ make sub-directories in the current working directory.
        """
        # Deal with multiple parameters (same as UNIX).
        if type(paths) == type(()):
            for path in paths:
                self._mkdir(path)
        else:
            self._mkdir(paths[0])


    def _mkdir(self, path):
        """ Make one directory with given path.
        """
        # If given an absolute path.
        if path[0] == '/':
            self.client.makeMailBox(path)
        else:
            self.client.makeMailBox(self.curr + '/' + path)

    def rmdir(self, *paths):
        """ remove sub-directories in the current working directory.
        """
        # Deal with multiple parameters (same as UNIX).
        if type(paths) == type(()):
            for path in paths:
                self._rmdir(path)
        else:
            self._rmdir(paths[0])

    def _rmdir(self, path):
        """ Remove one directory with given path.
        """
        # If given an absolute path.
        if path[0] == '/':
            self.client.removeMailBox(path)
        else:
            self.client.removeMailBox(self.curr + '/' + path)

if __name__ == '__main__':
    """ Program entry.
    """
    import sys

    # Initialize the argument parser.
    parser = argparse.ArgumentParser(
                        description = 'UNIX bash like IMAP4 client.',
                        add_help    = False)
    option_group = parser.add_argument_group("Options")
    option_group.add_argument('host',
                              metavar = 'host',
                              nargs   = '?',
                              help    = 'imap host')
    option_group.add_argument('username',
                              metavar = 'username',
                              nargs   = '?',
                              help    = 'username')
    option_group.add_argument('password',
                              metavar = 'password',
                              nargs   = '?',
                              help    = 'password')

    # Check user input.
    # Print the help information, if user does not provide any command line parameter.
    if len(sys.argv)==1:
        parser.print_help()
        sys.exit(0)
    # Parse the command line arguments.
    args = parser.parse_args()
    # Execute the program.
    Cmd(args.host, args.username, args.password)
