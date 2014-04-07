import socket
import ssl
import random
import re
from util import printd

# This module follows RFC2060 and RFC3501. Comments will reference the section
# number and document name at end, such as [2.3.1, RFC 2060]. If it mensioned
# in both document, the document name will be omited.

# The default port for IMAP/IMAPrev1 with SSL.
IMAP_SSL_PORT = 993
# Line terminator in IMAP/IMAPrev1
CRLF = '\r\n'

# IMAP states. [6]
STATES = ('NONAUTH', 'AUTH', 'SELECTED', 'LOGOUT')

# IMAP commands. [6]
# For any existing IMAP command 'c':
#     - COMMANDS['c'][0] are their valid states.
#     - COMMANDS['c'][1] are their switch cases (if not None).
#       If the success command is received (OK response), the state should
#       switch to COMMANDS['c'][1][0]; else if the fail command is received (NO
#       response), the state should switch to COMMANDS['c'][1][1]. However, A
#       rejected command (BAD response) never changes the state of the
#       connection or of the selected mailbox.
COMMANDS = {
        # command         valid states                              success     fail
        'APPEND':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'AUTHENTICATE': (('NONAUTH'                              ),('AUTH',     None  )),
        'CAPABILITY':   (('NONAUTH', 'AUTH', 'SELECTED', 'LOGOUT'),(None,       None  )),
        'CHECK':        ((                   'SELECTED'          ),(None,       None  )),
        'CLOSE':        ((                   'SELECTED'          ),('AUTH',     None  )),
        'COPY':         ((                   'SELECTED'          ),(None,       None  )),
        'CREATE':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'DELETE':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'DELETEACL':    ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'EXAMINE':      ((           'AUTH', 'SELECTED'          ),('SELECTED', 'AUTH')),
        'EXPUNGE':      ((                   'SELECTED'          ),(None,       None  )),
        'FETCH':        ((                   'SELECTED'          ),(None,       None  )),
        'GETACL':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'GETANNOTATION':((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'GETQUOTA':     ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'GETQUOTAROOT': ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'MYRIGHTS':     ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'LIST':         ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'LOGIN':        (('NONAUTH'                              ),('AUTH',     None  )),
        'LOGOUT':       (('NONAUTH', 'AUTH', 'SELECTED', 'LOGOUT'),('LOGOUT',   None  )),
        'LSUB':         ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'NAMESPACE':    ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'NOOP':         (('NONAUTH', 'AUTH', 'SELECTED', 'LOGOUT'),(None,       None  )),
        'PARTIAL':      ((                   'SELECTED'          ),(None,       None  )),
        'PROXYAUTH':    ((           'AUTH'                      ),(None,       None  )),
        'RENAME':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'SEARCH':       ((                   'SELECTED'          ),(None,       None  )),
        'SELECT':       ((           'AUTH', 'SELECTED'          ),('SELECTED', 'AUTH')),
        'SETACL':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'SETANNOTATION':((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'SETQUOTA':     ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'SORT':         ((                   'SELECTED'          ),(None,       None  )),
        'STATUS':       ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'STORE':        ((                   'SELECTED'          ),(None,       None  )),
        'SUBSCRIBE':    ((           'AUTH', 'SELECTED'          ),(None,       None  )),
        'THREAD':       ((                   'SELECTED'          ),(None,       None  )),
        'UID':          ((                   'SELECTED'          ),(None,       None  )),
        'UNSUBSCRIBE':  ((           'AUTH', 'SELECTED'          ),(None,       None  ))
        }

# Regular expression to match IMAP4 iteral. [4.3]
Literal = re.compile(r'.*{(?P<size>\d+)}$')

class Error(Exception): pass

# Lower level exception.
# This exception occors if a non-existing command is given or invaild state for
# the command is in.
class InvalidCommandError(Error): pass

class IMAPServer(object):
    """ The IMAP server with simplified API.

    This class provide convenient api for IMAP client.

    Arguments:
        sock:     The client socket connets to the IMAP server.
        buffer:   The file like object stores the IMAP server response.
        state:    The current state.
    """

    def __init__(self, host):
        """ Construct the IMAP client.
        
        This constructor will establish the connection and receive the initial
        greeting from the server.

        Args:
            host: The address of the IMAP server.

        Raise:
            InvalidCommandError: If a non-existing command is given or invaild
                                 state for the command is in.
        """

        # Establishment of a client/server network connection.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = ssl.wrap_socket(self.sock)
        self.sock.connect((host, IMAP_SSL_PORT))
        self.buffer = self.sock.makefile('rb')

        # Receive an initial greeting from the server.
        tag, init_greeting = self._recv_line()
        # Set the initial state by initial greeting. [3]
        type = init_greeting.split(' ')[0]
        if type == 'PREAUTH':
            self.state = 'AUTH'
        elif type == 'OK':
            self.state = 'NONAUTH'
        else:
            raise InvalidCommandError(init_greeting)

    def _interact(self, command, *params):
        """ Make one client/server interaction.

        An IMAP4 interactions consist of:
            *   Command  (a client command)
            *   Response (server data and a server completion result response)
        This function not only complete an IMAP4 interaction, but also interact
        with the response, which includes change status, etc.

        Args:
            command: The IMAP4 command.
            params:  The parameter passed with command.

        Raise:
            InvalidCommandError: If a non-existing command is given or invaild
                                 state for the command is in.

        Returns:
            A tuple of three elements: tag, tagged response and untagged
            response. Tag and tagged response are strings, and untagged response
            is a list of string.
        """

        # Send client command to IMAP4 server.
        command = command.upper()
        if command not in COMMANDS:
            raise InvalidCommandError('Command ' + command + ' dees not exists')
        if self.state not in COMMANDS[command][0]:
            raise InvalidCommandError('Command ' + command + ' is not available in ' + self.state + ' state')
        # Generate a different tag for each command. [2.2.1]
        # The tag is generated to be a random 6-bit hexadecimal value.
        tag = hex(random.randint(1048576, 16777215))[2:]
        params = ' ' + ' '.join(params) if len(params) > 0 else ''
        msg = tag + ' ' + command + params + CRLF
        self.sock.send(msg)
        printd('\n' + msg)

        # Receive server response.
        tagged_response = ''
        untagged_response = []
        while 1:
            curr_tag, info = self._recv_line()
            # Decide action by type.
            if curr_tag == '*':
                # Add quoted string if literal.
                match = re.match(Literal, info)
                if match:
                    size = match.group('size')
                    # Read the literal and the tail.
                    quoted = self.buffer.read(int(size)) + self.buffer.readline()
                    printd(quoted)
                    info += CRLF + quoted[:-2]
                untagged_response.append(info)
            elif curr_tag == '+':
                # [7.5]
                self._recv_line()
            elif curr_tag == tag:
                tagged_response = info
                break
            else:
                raise InvalidCommandError('Receive invalid tagged response')

        # Analysis and interact with server response.
        # Check response type.
        type, tagged_data = tagged_response.split(' ', 1)
        if type == 'BAD':
            raise InvalidCommandError(tagged_data)
        # Update current states.
        new_state = {
                'OK': COMMANDS[command][1][0],
                'NO': COMMANDS[command][1][1]
                }.get(type, None)
        if new_state != None:
            self.state = COMMANDS[command][1][0]
            printd('\n[current state swith to ' + self.state + ']\n')

        # Return response for further processing in higher level functions.
        return type, tagged_data, untagged_response

    def _recv_line(self):
        """ Receive one response line with ending CRLF removed.
        """
        msg_line = ''
        # Retrieve an complete line end with CRLF.
        while 1:
            line = self.buffer.readline()
            msg_line += line
            if line[-2:] == CRLF: break
        printd(msg_line)
        # Remove the ending CRLF.
        return msg_line[:-2].split(' ', 1)

    # IMAP4 Commands
    # Each of the following fucntion reacting the same as the IMAP command with
    # identical name. It returns a list of three elements:
    #   - response type(OK/NO)
    #   - a list of untagged informations
    #   - tagged response information
    # Because of time, only simple commands have been implemented.
    # TODO : complete the simplified command (e.g. SELECT without randomly),
    #        implement other commands.
    #def APPEND(): pass
    #def AUTHENTICATE(): pass
    def CAPABILITY(self):                        return self._interact('CAPABILITY')
    def CHECK(self):                             return self._interact('CHECK')
    def CLOSE(self):                             return self._interact('CLOSE')
    def COPY(self, messages, mailbox):           return self._interact('COPY', messages, mailbox)
    def CREATE(self, mailbox):                   return self._interact('CREATE', mailbox)
    def DELETE(self, mailbox):                   return self._interact('DELETE', mailbox)
    def DELETEACL(self, mailbox):                return self._interact('DELETEACL', mailbox)
    def EXPUNGE(self):                           return self._interact('EXPUNGE')
    def FETCH(self, messages, parts):            return self._interact('FETCH', messages, parts)
    def GETACL(self):                            return self._interact('GETACL')
    def GETANNOTATION(self):                     return self._interact('GETANNOTATION')
    def GETQUOTAROOT(self, mailbox):             return self._interact('GETQUOTAROOT')
    def LIST(self, directory='""', pattern='*'): return self._interact('LIST', directory, pattern)
    def LOGIN(self, username, password):         return self._interact('LOGIN', username, password)
    def LOGOUT(self):                            return self._interact('LOGOUT')
    def LSUB(self, directory='""', pattern='*'): return self._interact('LSUB', directory, pattern)
    def MYRIGHTS(self, mailbox):                 return self._interact('MYRIGHTS', mailbox)
    def NAMESPACE(self):                         return self._interact('NAMESPACE')
    def NOOP(self):                              return self._interact('NOOP')
    def PARTIAL(self, num, part, start, length): return self._interact('PARTIAL', num, part, start, length)
    def PROXYAUTH(self, user):                   return self._interact('PROXYAUTH', user)
    def RENAME(self, old_mailbox, new_mailbox):  return self._interact('RENAME', old_mailbox, new_mailbox)
    #def SEARCH(self): pass
    def SELECT(self, mailbox):                   return self._interact('SELECT', mailbox)
    def SELECTACL(self, mailbox, who, what):     return self._interact('SELECT', mailbox, who, what)
    def SETANNOTATION(self, *annotations):       return self._interact('SETANNOTATION', *annotations)
    def SETQUOTA(self, root, limits):            return self._interact('SETQUOTA', root, limits)
    #def SORT(self): pass
    def STATUS(self, mailbox, names):            return self._interact('STATES', mailbox, names)
    #def STORE(self, messages, command, flags): pass
    def SUBSCRIBE(self, mailbox):                return self._interact('SUBSCRIBE', mailbox)
    #def THREAD(): pass
    #def UID(self): pass
    def UNSUBSCRIBE(self, mailbox):              return self._interact('UNSUBSCRIBE', mailbox)
    #def xatom(self): pass


if __name__ == '__main__':
    """ The entry for debugging.
    """
    imap_server = IMAPServer('fcspostoffice.cs.dal.ca')
    while 1:
        command = raw_input('\nENTER: ')
        command = command.split(' ')
        if command[0] == "!":
            # Test the function with token '!' at begining.
            printd('\n[call function ' + command[1].upper() + '(' + repr(command[2:])[1:-1] + ')]\n')
            getattr(imap_server, command[1].upper())(*command[2:])
        else:
            # Direct test the usability of the command.
            imap_server._interact(command[0], *command[1:])
