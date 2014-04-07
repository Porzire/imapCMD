import server
import re
from util import printd

class IMAPClient(object):
    """ IMAP client.

    Arguments:
        server: IMAP server.
    """

    def __init__(self, host, username, password):
        """ Initialize the client with connect established.

        Args:
            host:     The address of the IMAP SSL host.
            username: The username.
            password: The password.
        """
        self.server = server.IMAPServer(host)
        self.server.LOGIN(username, password)

    def getMailBoxs(self, directory='""'):
        """ Return a list of mailboxs.

        Args:
            directory: The parent diretory of the retrieving mailbox list.
        """
        mailboxs = []
        for line in self.server.LIST(directory)[2]:
            mailboxs.append(line.split(' ')[-1][1:-1])
        return mailboxs

    # Other mail box operations.
    def makeMailBox(self, path):                 self.server.CREATE(path)
    def removeMailBox(self, path):               self.server.DELETE(path)
    def renameMailBox(self, old_name, new_name): self.server.RENAME(path, old_name, new_name)

    def getEmails(self, directory, part='UID', range='1:*', raw=False):
        """ Get information of a list of emails.

        Args:
            directory: The mailbox where the retrieving email stays.
            part:      The part of the email to be retrieve.
            range:     The range of email list in the mailbox.
            raw:       Returns unprocessed information if true.
        """
        # If the directory cannot be SELECT, return an empty list.
        if self.server.SELECT(directory)[0] == 'NO':
            return []
        info = self._getInfo(directory, part, range, raw)
        self.server.CLOSE()
        return info

    def _getInfo(self, directory, part='UID', range='1:*', raw=False):
        """ Get information of a list of emails from a seleted mailbox.

        Args:
            directory: The mailbox where the retrieving email stays.
            part:      The part of the email to be retrieve.
            range:     The range of email list in the mailbox.
            raw:       Returns unprocessed information if true.
        """
        lines = self.server.FETCH(range, part)[2]
        if raw: return lines
        result = []
        for line in lines:
            line = line.split(server.CRLF)
            #print repr('[line]\n' + repr(line[1:-2]))
            if len(line) > 1:
                data = '\n'.join(line[1:-2])
                result.append(data)
            else:
                data = line[0].split(' ', 2)[2][1:-1]
                # Only available for single part element.
                # TODO : deal with multiple part.
                data = data.split(' ')
                result.append({data[0]:data[1]})
        return result

    def getEmail(self, directory, num):
        """ get a complete readable email from directory.

        Args:
            directory: The mailbox where the retrieving email stays.
            num:       The email number in the mailbox.
        """
        if self.server.SELECT(directory)[0] == 'NO':
            return ""
        head = self._getInfo(directory, '(RFC822.HEADER.LINES (Subject From To Date))', str(num))
        text = self._getInfo(directory, 'RFC822.TEXT', str(num))
        self.server.CLOSE()
        return head[0], text[0]

    def logout(self):
        """ Logout the IMAP4 server.
        """
        self.server.LOGOUT()

if __name__ == '__main__':
    """ The entry for debugging.
    """
