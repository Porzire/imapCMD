IMAP Command Line Interface
===========================

>Author:  Jie Mei  
>Date:    April 7, 2014  
>Version: 0.1  

Introduction
------------
This program provides a UNIX like IMAP command line interface. After login to
the IMAP4 host, user could use IMAP4 mail server as the UNIX file system.

This program is written in Python and follows the Google Python Style Guild.

__NOTE__: This program only work with IMAP4/IMAP4rev1 server with SSL.

Usage
-----
This program does not need to compile. Access to /imapCMD folder and run the
following command in the command line:

```
./imapCMD.py [host] [username] [password]
```

__NOTE__: Run with command `python imapCMD.py` will print debugging information.

`[host]`, `[username]`, `[password]` are the optional placeholder for host
address, username and password. The program needs all these information to
initilize services. If any of three does not provided in the command line, the
program will ask user to input when start running.
 
Once the program reveived initilizing informations and get start, user could
use UNIX command to operate. The following commands are available with some
restrictions:

* `ls`  
    list the subdirectories in the current working directory.
* `pwd`  
    display the current working directory.
* `logout`  
    logout the IMAP server and program terminates.
* `exit`  
    alternative way terminate the program, same as `logout`.
* `lm`  
    list the number of mails in the current working directory.
* `cat num`  
    display the emil in the current working directory with mail id `num`.
* `cd path`  
    access the directory path. Step back to the parent directory if `path` is
    `..`.
* `mkdir dir1...`  
    make sub-directories in the current working directory.
* `rmdir dir1...`  
    remove sub-directories in the current working directory.

NOTE: Directory is the abstract representation of mailbox in IMAP server.

Code Structure
--------------
This program consists of four Python source files: `server.py`, `client.py`,
`util.py`, `imapCMD.py`. Each class have their own responsibility:

* `imapCMD.py`  
    Provide user interface and define UNIX like command. It deal with user input,
    format and print out required data. It builds the user command with high-
    level function from `client.py`.
* `client.py`  
    Provide high-level functions. It defines the function direct operate
    mailbox and email, such as `getMailBox()` and `getEmail()`.
* `server.py`  
    Provide low-level functions. It defines function communicate with IMAP4
    server. It deal with service connection, query and responsew following
    RFC2060 and RFC3101. It provides convient API to send request and returns
    formated response.
* `util.py`  
    Provide utility functions. It helps to improve the readability and
    reusability of the code. Some functions are `printd()` for printing debuging
    informations and `printe()` for printing exception informations.

They related in the following graph:

                    +---------------------------+
                    |        imapCMD.py         |
                    +---------------------------+
                     ||            ||
                     ||            VV
                     ||  +----------------------+
                     ||  |      client.py       |
                     ||  +----------------------+
                     ||     ||              ||
                     ||     ||              VV
                     ||     ||    +-------------+
                     ||     ||    |  server.py  |
                     ||     ||    +-------------+
                     ||     ||           ||
                     VV     VV           VV
                    +---------------------------+
                    |         util.py           |
                    +---------------------------+

 Each function is fully documented in the comments preceding the code.  Please
 read the source files for more information.
